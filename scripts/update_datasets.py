import csv
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

disc_env = {}
try:
    with open('options.json') as f:
        opts = json.load(f)
    for item in opts:
        if item.get('name') == 'disciplineCode':
            for case in item.get('cases', []):
                for v in case.get('values', []):
                    slug = v.get('disciplineNameUrlSlug')
                    env = v.get('environment')
                    if slug and env:
                        disc_env[slug] = env
except Exception as e:
    print("Warning loading options.json:", e)

def get_environment(discipline):
    if discipline in disc_env:
        return disc_env[discipline]
    if 'short-track' in discipline or 'indoor' in discipline:
        return 'indoor'
    return 'outdoor'

def format_subword(p):
    if not p: return ''
    lower = p.lower()
    if lower.startswith('mc') and len(p) > 2:
        return 'Mc' + p[2].upper() + p[3:].lower()
    if lower.startswith("o'") and len(p) > 2:
        return "O'" + p[2].upper() + p[3:].lower()
    return p[0].upper() + p[1:].lower()

def format_token(tok):
    return '-'.join(format_subword(p) for p in tok.split('-'))

def format_competitor(name, is_relay=False):
    if is_relay or not name:
        return name
    tokens = name.split(' ')
    out = []
    for tok in tokens:
        has_lower = any(c.islower() for c in tok)
        has_upper = any(c.isupper() for c in tok)
        if has_lower and not tok.lower().startswith('mc') and not tok.lower().startswith("o'"):
            out.append(tok)
        elif len(tok) == 2 and tok[1] == '.':
            out.append(tok)
        elif has_upper:
            out.append(format_token(tok))
        else:
            out.append(tok)
    return ' '.join(out)

def process_file(filepath):
    tmp_path = filepath + '.tmp'
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fin, \
             open(tmp_path, 'w', encoding='utf-8', newline='', errors='replace') as fout:
            reader = csv.reader(fin)
            writer = csv.writer(fout)
            
            try:
                header = next(reader)
            except StopIteration:
                return (filepath, 0, "empty file")
            
            if not header:
                return (filepath, 0, "empty header")

            has_env = 'environment' in header
            if not has_env:
                out_header = header + ['environment']
            else:
                out_header = header
            
            writer.writerow(out_header)

            comp_idx = header.index('competitor') if 'competitor' in header else -1
            type_idx = header.index('type') if 'type' in header else -1
            disc_idx = header.index('discipline') if 'discipline' in header else (
                header.index('normalized_discipline') if 'normalized_discipline' in header else -1
            )
            env_idx = header.index('environment') if has_env else -1

            rows_count = 0
            for row in reader:
                if not row:
                    continue
                rows_count += 1
                is_relay = (type_idx >= 0 and type_idx < len(row)) and (row[type_idx] == 'relays')

                if comp_idx >= 0 and comp_idx < len(row):
                    row[comp_idx] = format_competitor(row[comp_idx], is_relay)
                
                disc = row[disc_idx] if (disc_idx >= 0 and disc_idx < len(row)) else ''
                env = get_environment(disc)

                if has_env:
                    if env_idx < len(row):
                        row[env_idx] = env
                    else:
                        row.append(env)
                else:
                    row.append(env)

                writer.writerow(row)
        
        os.replace(tmp_path, filepath)
        return (filepath, rows_count, "ok")
    except Exception as e:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass
        return (filepath, 0, str(e))

if __name__ == '__main__':
    targets = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            targets.extend(glob.glob(arg, recursive=True))
    else:
        # Default targets
        targets.extend(glob.glob('data/processing/combined/all-time/*.csv'))
        targets.extend(glob.glob('data/processing/combined/seasons/**/*.csv', recursive=True))
        targets.extend(glob.glob('data/datasets/all-time/*.csv'))
        targets.extend(glob.glob('data/datasets/seasons/*_track_field_performances.csv'))

    targets = sorted(list(set(targets)))
    print(f"Found {len(targets)} files to process.")
    t0 = time.time()
    with Pool() as pool:
        for i, (fp, rows, status) in enumerate(pool.imap_unordered(process_file, targets)):
            if status != "ok":
                print(f"[{i+1}/{len(targets)}] ERR: {fp} - {status}")
            elif (i + 1) % 500 == 0 or (i + 1) == len(targets):
                print(f"[{i+1}/{len(targets)}] Processed {fp} ({rows} rows)")
    t1 = time.time()
    print(f"Done processing in {t1-t0:.2f}s!")

