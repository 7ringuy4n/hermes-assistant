"""Quoted conversion sources are explicit data, not recalled attachment text."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'hermes/main/plugins/zalo'))
from attachment import merge_inbound_quote_media
from classify_client import normalize_task_details, plan_is_image_analyze_chat
from job_prompt import workflow_instruction


def main():
    cases = (
        ('quote', {'cliMsgType': 46, 'attach': json.dumps({'title': 'slides.pptx',
                  'href': 'https://files.example.test/slides.pptx', 'params': {'fileExt': 'pptx'}})}, 'pptx', 'pdf'),
        ('quoted', {'msgType': 'share.file', 'content': {'title': 'slides.pptx',
                    'href': '/opt/data/media/inbound/slides.pptx'}}, 'pptx', 'pdf'),
        ('quoted', {'msgType': 'share.file', 'content': {'title': 'sheet.xlsx',
                    'href': '/data/media/inbound/sheet.xlsx'}}, 'xlsx', 'docx'),
    )
    for index, (key, quote, source_ext, target) in enumerate(cases, 1):
        print(f'running test case {index}/5 quote-reply {source_ext} to {target}')
        message = {key: quote, 'text': 'convert this quoted file'}
        media, resolved = merge_inbound_quote_media(message, None)
        assert media and media['kind'] == 'file' and media['fileName'].endswith('.' + source_ext)
        assert resolved['media'] == media and resolved[key] == quote
        details = normalize_task_details({'task_type': 'file_processing', 'output_type': target,
            'artifact_operation': 'convert'}, [message['text']], 'file')
        contract = workflow_instruction(message['text'], details[0], [media['url']], original_request=message['text'])
        assert json.loads(contract.split('\n\n')[-2])['original_request'] == message['text']
        assert media['url'] in contract and '"artifact_operation": "convert"' in contract
        assert not plan_is_image_analyze_chat({'artifact_operation': 'convert', 'output_type': target})
    print('running test case 4/5 missing or escaping quoted source is not replaced with another file')
    for path in ('/etc/slides.pptx', '/opt/data/media/../../secret.pptx', ''):
        media, resolved = merge_inbound_quote_media({'quoted': {'msgType': 'share.file',
            'content': {'title': 'missing.pptx', 'href': path}}}, None)
        assert media is None and 'media' not in resolved
    print('running test case 5/5 explicit direct attachment keeps its own source identity')
    direct = {'kind': 'file', 'url': '/opt/data/media/inbound/direct.pptx', 'fileName': 'direct.pptx'}
    media, _ = merge_inbound_quote_media({'quoted': cases[0][1]}, direct)
    assert media is direct
    print('PASS quoted file conversion source contracts')


if __name__ == '__main__':
    main()
