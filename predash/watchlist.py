"""Portable, bounded watch codes for a bookmark or an exported backup."""
import json
import re

MAX_WATCH=8

def clean_codes(values):
    result=[]
    for value in values:
        code=str(value).strip()
        if re.fullmatch(r'[0-9]{6}',code) and code not in result:
            result.append(code)
        if len(result)==MAX_WATCH:break
    return result

def restore_backup(payload):
    try:
        decoded=json.loads(payload)
        if not isinstance(decoded,dict) or decoded.get('version')!=1 or not isinstance(decoded.get('codes'),list):
            raise ValueError
        return clean_codes(decoded['codes'])
    except (ValueError,TypeError,UnicodeDecodeError):
        raise ValueError('관심종목 백업 파일 형식을 확인하세요.') from None

def clean_names(names,codes):
    if not isinstance(names,dict):return {}
    return {code:str(names[code]).strip()[:80] for code in clean_codes(codes)
            if code in names and isinstance(names[code],str) and names[code].strip() and names[code].strip()!=code}

def backup_names(payload):
    codes=restore_backup(payload)
    decoded=json.loads(payload)
    return clean_names(decoded.get('names',{}),codes)

def export_backup(codes,names=None):
    codes=clean_codes(codes)
    payload={'version':1,'codes':codes}
    if names:payload['names']=clean_names(names,codes)
    return json.dumps(payload,ensure_ascii=False,indent=2)

