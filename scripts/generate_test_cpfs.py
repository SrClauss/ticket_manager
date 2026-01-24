#!/usr/bin/env python3
"""Generate CSV test files with CPFs for upload validation testing.

Creates multiple CSV files in the output directory:
 - valid.csv: rows with valid CPFs
 - invalid_cpf.csv: rows with syntactically invalid CPFs
 - missing_fields.csv: rows with random missing required fields
 - duplicate_cpfs.csv: rows with duplicate CPFs within the file
 - mixed.csv: mixed cases

Usage: ./scripts/generate_test_cpfs.py --outdir scripts/test_data --rows 100
"""

import csv
import os
import random
import argparse

HEADERS = ['Nome','Email','CPF','Telefone','Empresa','Tipo Ingresso']


def calc_cpf_check_digits(digs):
    # digs: list of first 9 digits
    s = sum(digs[i] * (10 - i) for i in range(9))
    r = s % 11
    d1 = 0 if r < 2 else 11 - r
    s2 = sum(digs[i] * (11 - i) for i in range(9)) + d1 * 2
    r2 = s2 % 11
    d2 = 0 if r2 < 2 else 11 - r2
    return d1, d2


def generate_cpf(formatted=True):
    # ensure not all digits equal
    while True:
        base = [random.randint(0,9) for _ in range(9)]
        if len(set(base)) > 1:
            break
    d1,d2 = calc_cpf_check_digits(base)
    digits = base + [d1, d2]
    if formatted:
        s = ''.join(str(d) for d in digits)
        return f"{s[0:3]}.{s[3:6]}.{s[6:9]}-{s[9:11]}"
    else:
        return ''.join(str(d) for d in digits)


def corrupt_cpf(cpf):
    # produce an invalid cpf by changing last digit
    s = ''.join(ch for ch in cpf if ch.isdigit())
    if len(s) != 11:
        return cpf
    lst = list(s)
    lst[-1] = str((int(lst[-1]) + random.randint(1,9)) % 10)
    new = ''.join(lst)
    return f"{new[0:3]}.{new[3:6]}.{new[6:9]}-{new[9:11]}"


def random_phone():
    return f"+55{random.randint(11,99)}9{random.randint(10000000,99999999)}"


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=HEADERS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def make_rows(n):
    rows = []
    for i in range(1, n+1):
        nome = f"Usuario Teste {i}"
        email = f"user{i}@example.com"
        cpf = generate_cpf()
        tel = random_phone()
        empresa = random.choice(['Acme Ltda','Globex','Initech','Umbrella'])
        tipo = random.randint(1,3)
        rows.append({'Nome': nome, 'Email': email, 'CPF': cpf, 'Telefone': tel, 'Empresa': empresa, 'Tipo Ingresso': tipo})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--outdir', default='scripts/test_data')
    parser.add_argument('--rows', type=int, default=50)
    args = parser.parse_args()

    outdir = args.outdir
    n = args.rows

    # base valid rows
    valid = make_rows(n)
    write_csv(os.path.join(outdir, 'valid.csv'), valid)

    # invalid cpf: corrupt last digit for half of rows
    invalid = []
    for r in valid:
        nr = r.copy()
        if random.random() < 0.6:
            nr['CPF'] = corrupt_cpf(nr['CPF'])
        else:
            nr['CPF'] = nr['CPF'][:-1]  # truncate to make invalid
        invalid.append(nr)
    write_csv(os.path.join(outdir, 'invalid_cpf.csv'), invalid)

    # missing fields: randomly drop Nome/Email/CPF in some rows
    missing = []
    for r in valid:
        nr = r.copy()
        if random.random() < 0.15:
            nr['Email'] = ''
        if random.random() < 0.15:
            nr['Nome'] = ''
        if random.random() < 0.15:
            nr['CPF'] = ''
        missing.append(nr)
    write_csv(os.path.join(outdir, 'missing_fields.csv'), missing)

    # duplicates: duplicate some CPFs
    dup = []
    base = make_rows(max(1, n//3))
    for r in base:
        dup.append(r.copy())
        # duplicate each twice
        dup.append(r.copy())
    # fill up to n
    while len(dup) < n:
        dup.append(random.choice(base).copy())
    write_csv(os.path.join(outdir, 'duplicate_cpfs.csv'), dup[:n])

    # mixed: combine some good, some bad
    mixed = []
    for i in range(n):
        choice = random.random()
        if choice < 0.5:
            mixed.append(valid[i].copy())
        elif choice < 0.7:
            mixed.append(invalid[i].copy())
        elif choice < 0.85:
            mixed.append(missing[i].copy())
        else:
            mixed.append(dup[i % len(dup)].copy())
    write_csv(os.path.join(outdir, 'mixed.csv'), mixed)

    print('Generated test CSVs in', os.path.abspath(outdir))

if __name__ == '__main__':
    main()
