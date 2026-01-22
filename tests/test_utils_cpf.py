import asyncio
import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.utils.validations import ensure_cpf_unique


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_one(self, query=None, sort=None):
        query = query or {}
        # supports {'evento_id':..., '$or':[...]} minimal
        for d in self.docs:
            ok = True
            for k, v in query.items():
                if k == '$or':
                    found_any = False
                    for sub in v:
                        # sub is like {'participante_id': 'x'} or {'participante_cpf': 'y'}
                        for sk, sv in sub.items():
                            if d.get(sk) == sv:
                                found_any = True
                                break
                        if found_any:
                            break
                    if not found_any:
                        ok = False
                        break
                else:
                    if d.get(k) != v:
                        ok = False
                        break
            if ok:
                return d
        return None


class FakeDB:
    def __init__(self, ingressos=None):
        self.ingressos_emitidos = FakeCollection(ingressos or [])


@pytest.mark.asyncio
async def test_ensure_cpf_unique_success():
    ev = 'evt1'
    db = FakeDB(ingressos=[])
    cpf = '529.982.247-25'

    res = await ensure_cpf_unique(db, ev, participante_id=None, cpf_raw=cpf)
    assert res == '52998224725'


@pytest.mark.asyncio
async def test_ensure_cpf_unique_invalid_cpf():
    ev = 'evt1'
    db = FakeDB(ingressos=[])
    cpf = '111.111.111-11'

    with pytest.raises(HTTPException) as exc:
        await ensure_cpf_unique(db, ev, participante_id=None, cpf_raw=cpf)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_ensure_cpf_unique_duplicate():
    ev = 'evt1'
    # existing ingresso with participante_cpf
    db = FakeDB(ingressos=[{'evento_id': ev, 'participante_cpf': '52998224725'}])

    with pytest.raises(HTTPException) as exc:
        await ensure_cpf_unique(db, ev, participante_id=None, cpf_raw='529.982.247-25')
    assert exc.value.status_code == 409
