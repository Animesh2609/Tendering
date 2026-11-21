"""FastAPI adapter. PostgreSQL stores requests; model data remains read-only."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import json
from pathlib import Path
from app.service import ReviewedRecommendationService
import secrets
from typing import Literal
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, select, text
from sqlalchemy.orm import DeclarativeBase, Session
from recommendation_api import RecommendationService

class Base(DeclarativeBase):pass
class Run(Base):
    __tablename__='recommendation_runs'
    id=Column(Integer,primary_key=True)
    created_at=Column(DateTime(timezone=True),nullable=False)
    request=Column(JSON,nullable=False)
    response=Column(JSON,nullable=False)

class RecommendationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    user_id:int|None=Field(default=None,ge=0)
    history_items:list[int]=Field(default_factory=list,max_length=10000)
    k:int=Field(default=20,ge=1,le=150)
    mode:Literal['CausalEPP','CP_H','CP_Im']='CausalEPP'

def create_app(service=None,engine=None,api_key=None):
    @asynccontextmanager
    async def lifespan(app):
        key=api_key or os.environ.get('RECOMMENDATION_API_KEY','')
        if len(key)<24:raise RuntimeError('Set RECOMMENDATION_API_KEY to a random secret of at least 24 characters.')
        app.state.key=key
        if engine is None:
            url=os.environ.get('DATABASE_URL','')
            if not url.startswith('postgresql+psycopg://'):
                raise RuntimeError('DATABASE_URL must use postgresql+psycopg://.')
            app.state.db=create_engine(url,pool_pre_ping=True,connect_args={'connect_timeout':5})
        else:app.state.db=engine
        try:
            Base.metadata.create_all(app.state.db)
            report_path=os.environ.get('CALIBRATION_REPORT')
            policy=json.loads(Path(report_path).read_text()).get('policy_version') if service is None else None
            service_class=ReviewedRecommendationService if policy=='teammate_v2' else RecommendationService
            app.state.service=service or service_class(
                os.environ['MODEL_CHECKPOINT'],os.environ['DATA_DIR'],os.environ['CALIBRATION_REPORT'])
            yield
        finally:
            if engine is None:app.state.db.dispose()
    app=FastAPI(title='CausalEPP Recommendation Lab',version='1.0',lifespan=lifespan)
    def authorize(x_api_key:str=Header(default='')):
        if not secrets.compare_digest(x_api_key,app.state.key):raise HTTPException(401,'Invalid API key')
    @app.get('/health')
    def health():
        with Session(app.state.db) as session:session.execute(text('SELECT 1'))
        return {'status':'ready'}
    @app.get('/catalog',dependencies=[Depends(authorize)])
    def catalog(q:str='',limit:int=20):
        if not 1<=limit<=100 or len(q)>200:raise HTTPException(422,'Invalid query or limit')
        return [{'item_id':int(i),'title':title} for i,title in app.state.service.names.items()
                if q.casefold() in title.casefold()][:limit]
    @app.get('/model',dependencies=[Depends(authorize)])
    def model_info():
        s=app.state.service
        return {'checkpoint_sha256':s.checkpoint_hash,'catalog_size':s.num_items,
                'supported_calibration_k':[int(k) for k in s.report['results']],
                'policy':s.report.get('policy_version','original_calibration'),
                'limitations':'New users use training-popularity fallback. Scores are not accuracy probabilities.'}
    @app.get('/evaluation',dependencies=[Depends(authorize)])
    def evaluation():
        report=app.state.service.report
        return {'scope':report.get('scope'), 'limitations':report.get('limitations',[]),
                'results':{k:{mode:summary['All'] for mode,summary in value.get('summaries',{}).items()}
                           for k,value in report['results'].items()}}
    @app.post('/recommend',dependencies=[Depends(authorize)])
    def recommend(payload:RecommendationRequest):
        try:result=app.state.service.recommend(**payload.model_dump())
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc
        with Session(app.state.db) as session:
            record=Run(created_at=datetime.now(timezone.utc),request=payload.model_dump(),response=result)
            session.add(record);session.commit();session.refresh(record)
            return {'run_id':record.id,**result}
    @app.get('/runs',dependencies=[Depends(authorize)])
    def runs(limit:int=20):
        if not 1<=limit<=100:raise HTTPException(422,'limit must be 1–100')
        with Session(app.state.db) as session:
            records=session.scalars(select(Run).order_by(Run.id.desc()).limit(limit)).all()
            return [{'run_id':r.id,'created_at':r.created_at.isoformat(),'request':r.request,'response':r.response} for r in records]
    return app

app=create_app()
