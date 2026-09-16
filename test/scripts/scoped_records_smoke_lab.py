"""Real registry/Memory/Schedule scope authorization with isolated fixtures."""
import json
import subprocess
import uuid


def main():
    marker = "scope-qa-" + uuid.uuid4().hex
    code = r'''
import sys,json,uuid
sys.path.insert(0,'/opt/data/plugins/zalo')
import notes_client as notes
import schedule_client as schedules
import channels_client as channels
admin=next(x.partition('|')[0].strip() for x in open('/opt/data/zalo_admin_users.txt') if x.strip() and not x.startswith('#'))
group=channels.resolve_channel('test')
assert group and group['kind']=='group', 'registered_test_group_unavailable'
marker=MARKER
ids=[]
schedule_id=''
def execute(plan,principal=None):
    return notes.execute_note_plan(plan,thread_id=admin,thread_type='user',sender_id=principal or admin,admin_ids={admin})
try:
    print('running test case 1/5 admin creates group note without changing reply destination',flush=True)
    result=execute({'skill_action':'create','note_selector':{'scope':'group','scope_ref':'test'},'notes':[{'title':marker,'content':'Sample group-scoped content'}]})
    assert result['success'] and result['count']==1
    ids.append((result['items'][0]['id'],'zalo:group:'+group['external_id']))
    print('running test case 2/5 current DM excludes group and explicit group/all include it',flush=True)
    assert execute({'skill_action':'lookup','note_selector':{'query':marker}})['count']==0
    for scope in ('group','all'):
        selector={'scope':scope,'query':marker}
        if scope=='group': selector['scope_ref']='test'
        result=execute({'skill_action':'lookup','note_selector':selector})
        assert result['success'] and result['count']==1
    print('running test case 3/5 explicit DM resolves registry and owns its selected note',flush=True)
    result=execute({'skill_action':'create','note_selector':{'scope':'dm','scope_ref':admin},'notes':[{'title':marker+' DM','content':'Sample DM content'}]})
    assert result['success'] and result['count']==1
    ids.append((result['items'][0]['id'],'zalo:user:'+admin))
    result=execute({'skill_action':'lookup','note_selector':{'scope':'all','query':marker}})
    assert result['success'] and result['count']==2
    print('running test case 4/5 nonadmin cross-scope and all-scope mutation fail closed',flush=True)
    assert execute({'skill_action':'lookup','note_selector':{'scope':'group','scope_ref':'test'}},'sample-ordinary-principal')['error']=='record_scope_forbidden'
    assert execute({'skill_action':'delete','note_selector':{'scope':'all','match_all':True}})['error']=='all_scope_read_only'
    print('running test case 5/5 real group schedule is not visible via requester DM',flush=True)
    schedule_id='scope-qa-'+uuid.uuid4().hex
    result=schedules.create_schedule(schedule_id=schedule_id,cron_expr='0 6 * * *',text='Sample future test',fire_text='Sample future test',name=marker,
        origin={'platform':'zalo','thread_id':group['external_id'],'user_id':admin},context={'thread_id':group['external_id'],'thread_type':'group'},
        cadence='daily',timezone='Asia/Ho_Chi_Minh',enabled=False)
    assert result.get('ok') is True
    assert not any(row['id']==schedule_id for row in schedules.schedules_for_thread(admin,'user'))
    assert any(row['id']==schedule_id for row in schedules.schedules_for_record_scope({'scope':'group','scope_ref':'test'},thread_id=admin,thread_type='user',is_admin=True))
    assert any(row['id']==schedule_id for row in schedules.schedules_for_record_scope({'scope':'all'},thread_id=admin,thread_type='user',is_admin=True))
    print('PASS live scoped core records',flush=True)
finally:
    for note_id,scope in ids:
        result=notes._request('DELETE','/v1/notes/'+note_id+'?scope_id='+scope)
        assert result.get('success') is True
    if schedule_id:
        schedules.delete_schedule(schedule_id)
'''.replace("MARKER", repr(marker))
    result = subprocess.run(["docker", "exec", "assistant-hermes-1", "python", "-B", "-c", code], capture_output=True, text=True)
    print(result.stdout, end="")
    if result.returncode:
        # Tracebacks can contain runtime identities; surface only safe detail.
        raise RuntimeError("scoped_records_live_core_failed")


if __name__ == "__main__":
    main()
