import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app.backend import create_app
class FakeService:
    names={0:'Example book'};num_items=1;checkpoint_hash='test';report={'results':{'20':{}}}
    def recommend(self,**payload):
        if payload['history_items']:raise ValueError('Invalid test history')
        return {'recommendations':[{'item_id':0,'title':'Example book'}],'backend':'synthetic_test'}
class AppTests(unittest.TestCase):
    def test_auth_validation_persistence(self):
        db=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        key='test-key-'*4
        with TestClient(create_app(FakeService(),db,key)) as client:
            self.assertEqual(client.get('/health').status_code,200)
            self.assertEqual(client.get('/runs').status_code,401)
            headers={'X-API-Key':key}
            self.assertEqual(client.post('/recommend',headers=headers,json={'user_id':True}).status_code,422)
            self.assertEqual(client.post('/recommend',headers=headers,json={'history_items':[99]}).status_code,422)
            result=client.post('/recommend',headers=headers,json={'user_id':0})
            self.assertEqual(result.status_code,200)
            self.assertEqual(client.get('/runs',headers=headers).json()[0]['run_id'],result.json()['run_id'])
            self.assertEqual(client.get('/catalog?q=book',headers=headers).json()[0]['item_id'],0)
        with TestClient(create_app(FakeService(),db,key)) as client:
            self.assertEqual(len(client.get('/runs',headers=headers).json()),1)
        db.dispose()
    def test_streamlit_initial_render(self):
        from streamlit.testing.v1 import AppTest
        page=AppTest.from_file(str(__import__('pathlib').Path(__file__).resolve().parents[1]/'app/frontend.py')).run(timeout=15)
        self.assertFalse(page.exception)
        self.assertEqual(page.title[0].value,'Discover your next recommendation')
