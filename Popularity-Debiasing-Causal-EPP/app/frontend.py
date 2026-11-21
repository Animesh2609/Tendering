"""Run: streamlit run app/frontend.py"""
import os
import httpx
import streamlit as st

st.set_page_config(page_title='CausalEPP · Recommendation Lab',page_icon='◈',layout='wide')
st.markdown('''<style>.block-container{max-width:1160px;padding-top:2rem}h1{letter-spacing:-.04em}
[data-testid="stMetric"]{background:#142438;padding:18px;border-radius:12px}
</style>''',unsafe_allow_html=True)
st.caption('RECOMMENDATION LAB / CAUSAL EPP')
st.title('Discover your next recommendation')
st.write('Explore a frozen recommendation model and compare its popularity-calibration modes.')
url=os.environ.get('API_BASE_URL','http://127.0.0.1:8000').rstrip('/')
key=os.environ.get('RECOMMENDATION_API_KEY','')
def api(path,body=None):
    try:
        with httpx.Client(timeout=60,headers={'X-API-Key':key}) as client:
            r=client.get(url+path) if body is None else client.post(url+path,json=body)
        r.raise_for_status();return r.json()
    except (httpx.HTTPError,ValueError):
        st.error('The API could not complete this request. Check the backend, API key and selected settings.');return None
with st.sidebar:
    st.header('Your session')
    existing=st.radio('Profile',['Existing dataset user','New visitor'])
    uid=st.number_input('Mapped user ID',min_value=0,step=1) if existing.startswith('Existing') else None
    mode=st.selectbox('Recommendation mode',['CausalEPP','CP_H','CP_Im'])
    st.caption('CausalEPP: base ranking. CP_H: validation-selected balance. CP_Im: calibration-first.')
    k=st.selectbox('Recommendations',[10,20])
    st.caption('This is a local research console, not a user-login system.')
tab,history,about=st.tabs(['Recommendations','Saved runs','Model & evidence'])
with tab:
    query=st.text_input('Find items you have already used',placeholder='Search the catalog by title')
    matches=api('/catalog?q='+__import__('urllib.parse',fromlist=['quote']).quote(query)) if query else []
    selected=st.multiselect('Additional history',options=[x['item_id'] for x in matches or []],format_func=lambda i:next(x['title'] for x in matches if x['item_id']==i))
    if st.button('Get recommendations',type='primary'):
        with st.spinner('Ranking unseen items…'):
            result=api('/recommend',{'user_id':uid,'history_items':selected,'k':k,'mode':mode})
        if result:st.session_state['result']=result
    result=st.session_state.get('result')
    if result:
        if result['new_user']:st.info('New visitor: recommendations use training popularity. No personal embedding has been learned yet.')
        a,b,c=st.columns(3)
        a.metric('Items returned',len(result['recommendations']));b.metric('Calibration weight',f"{result['applied_calibration_weight']:.2f}");c.metric('Saved run',result['run_id'])
        st.caption(result['snapshot_policy'])
        for rank,item in enumerate(result['recommendations'],1):
            with st.container(border=True):
                st.subheader(f"{rank:02d} · {item['title']}")
                st.caption(f"Item {item['item_id']} · ranking score {item['base_ranking_score']:.4f} (not a probability)")
        st.download_button('Download this result',__import__('json').dumps(result,indent=2),'recommendations.json','application/json')
    else:st.info('Choose a profile and mode, then request a recommendation list.')
with history:
    st.write('Requests are saved in PostgreSQL for this shared local research console.')
    if st.button('Load saved runs'):
        rows=api('/runs')
        for row in rows or []:
            with st.expander(f"Run {row['run_id']} · {row['created_at']}"):st.json(row)
with about:
    st.warning('A running app does not prove accuracy improvement. Calibration can reduce ranking accuracy.')
    if st.button('Inspect model snapshot'):
        info=api('/model')
        if info:st.json(info)
    st.write('Use held-out Recall, Precision, NDCG and Hit Rate for ranking quality; use popularity JSD for calibration. Do not interpret the ranking score as accuracy.')

    if st.button('Show measured evaluation'):
        evidence=api('/evaluation')
        if evidence:
            rows=[]
            for cutoff,methods in evidence['results'].items():
                for name,summary in methods.items():
                    rows.append({'K':cutoff,'Method':name,'Users':summary['users'],**(summary['metrics'] or {})})
            if rows:st.dataframe(rows,hide_index=True,use_container_width=True)
            else:st.info('This snapshot does not include aggregate evaluation results.')
            st.write(evidence['scope'])
            for limitation in evidence['limitations']:st.caption(limitation)
