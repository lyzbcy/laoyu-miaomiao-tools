"""Bilibili tags: ordinary tags and a single exact activity-topic selection."""
import json
from browser import UIError
from gates import activity_plan

class BilibiliTopics:
    def __init__(self,p):self.p=p;self.b=p.b

    def chips(self):
        return self.b.js("JSON.stringify([...document.querySelectorAll('.label-item-v2-container')].filter(e=>e.getClientRects().length).map(e=>e.querySelector('.label-item-v2-content')?.innerText.trim()).filter(Boolean))")

    def verify_activity(self):
        topic=self.p.j.get('bilibili_activity_topic')
        if not topic:return True
        selected=self.b.js('''(()=>{return [...document.querySelectorAll('.label-item-v2-container,[class*=topic],[class*=activity]')].some(e=>e.getClientRects().length&&e.innerText.trim().replace(/^#/,'')===NAME)})()'''.replace('NAME',json.dumps(topic)))
        if not selected:raise UIError('Saved activity topic missing; do not publish')
        return True

    def ordinary(self,tag):
        if tag in self.chips():return 'added'
        errors=['当前tag为话题专用','不允许自定义添加','标签已被注册为活动标签']
        # A previous tag's fading toast cannot classify the next tag.
        if any(t in self.p.body() for t in errors):
            self.b.wait(lambda:not any(t in self.p.body() for t in errors),timeout=8)
        selector=self.p.one_visible(self.p.cfg['tag_input'])
        self.b.edit(selector,tag);self.b.enter(selector)
        def outcome():
            if tag in self.chips():return 'added'
            # Read only the visible error/toast; never infer an activity from a
            # missing tag, a slow validation or a generic input error.
            return 'activity_only' if any(x in self.p.body() for x in errors) else None
        return self.b.wait(outcome,timeout=10)

    def activity(self,topic):
        old=self.p.j.get('bilibili_activity_topic')
        if old:
            if old!=topic:raise UIError('One activity topic already selected; do not add another')
            return {'topic':old,'status':'already_selected'}
        self.b.tap(text='搜索更多话题 >')
        # The dialog's search input is discovered from visible DOM attributes,
        # never from an undocumented endpoint or a guessed candidate index.
        def search_input():
            return self.b.js("(()=>{const es=[...document.querySelectorAll('input')].filter(e=>e.getClientRects().length&&/话题/.test(e.placeholder)&&/搜索/.test(e.placeholder));if(es.length>1)throw Error('Activity search input ambiguous');if(!es.length)return false;es[0].setAttribute('data-activity-search','active');return true})()")
        self.b.wait(search_input,timeout=10)
        self.b.edit('input[data-activity-search=active]',topic);self.b.enter('input[data-activity-search=active]')
        def candidate():
            return self.b.js('''(()=>{const name=NAME;const es=[...document.querySelectorAll('button,[role=option],a,span,div')].filter(e=>e.getClientRects().length&&!e.closest('[contenteditable]')&&e.innerText.trim().replace(/^#/,'')===name);const leaf=es.filter(e=>!es.some(x=>x!==e&&e.contains(x)));if(leaf.length>1)throw Error('Activity candidate ambiguous');if(!leaf.length)return false;leaf[0].setAttribute('data-activity-candidate','active');return true})()'''.replace('NAME',json.dumps(topic)))
        self.b.wait(candidate,timeout=12)
        self.b.tap(selector='[data-activity-candidate=active]')
        # Do not claim success just because the search result was clicked.
        def selected():
            return self.b.js('''(()=>{const es=[...document.querySelectorAll('input')].filter(e=>e.getClientRects().length&&/话题/.test(e.placeholder)&&/搜索/.test(e.placeholder));if(es.length)return false;return [...document.querySelectorAll('.label-item-v2-container,[class*=topic],[class*=activity]')].some(e=>e.getClientRects().length&&e.innerText.trim().replace(/^#/,'')===NAME)})()'''.replace('NAME',json.dumps(topic)))
        self.b.wait(selected,timeout=10)
        self.p.j['bilibili_activity_topic']=topic;self.p.persist()
        return {'topic':topic,'status':'selected_and_read_back'}

    def apply(self):
        topics=self.p.item.get('topics',[])
        plan=activity_plan(topics,self.p.item.get('activity_topics',[]))
        existing=self.chips()
        if not self.p.j.get('bilibili_topics_started'):
            self.p.j['bilibili_default_topics']=existing
            self.p.j['bilibili_topics_started']=True;self.p.persist()
            for tag in existing:
                if tag in topics:continue
                self.b.js('''(()=>{const e=[...document.querySelectorAll('.label-item-v2-container')].find(e=>e.getClientRects().length&&e.querySelector('.label-item-v2-content')?.innerText.trim()===NAME);e?.querySelector('svg.close')?.dispatchEvent(new MouseEvent('click',{bubbles:true}));return true})()'''.replace('NAME',json.dumps(tag)))
                self.b.wait(lambda:tag not in self.chips(),timeout=6)
        blocked=[];ordinary=[];omitted=[]
        selected=self.p.j.get('bilibili_activity_topic') or plan['activity']
        if plan['activity']:self.activity(plan['activity'])
        for tag in plan['ordinary']:
            if self.ordinary(tag)=='added':ordinary.append(tag);continue
            blocked.append(tag)
            if not selected:self.activity(tag);selected=tag
            elif selected!=tag:omitted.append(tag)
        self.p.j['bilibili_actual_topics']=ordinary
        self.p.j['bilibili_activity_omitted']=omitted
        self.p.persist()
        return {'ordinary':ordinary,'activity':selected,'omitted_activity_limit':omitted,'activity_routed_from_tags':blocked}
