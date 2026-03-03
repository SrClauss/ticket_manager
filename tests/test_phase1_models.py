import pytest
from app.models.participante import ParticipanteCreate
from app.models.tipo_ingresso import TipoIngressoCreate


def test_participante_cpf_validator_valid():
    p = ParticipanteCreate(nome="João", email="joao@example.com", cpf="529.982.247-25")
    assert p.cpf == "52998224725"


def test_participante_cpf_validator_invalid():
    with pytest.raises(ValueError):
        ParticipanteCreate(nome="X", email="x@x.com", cpf="111.111.111-11")


def test_tipo_ingresso_defaults():
    t = TipoIngressoCreate(descricao="VIP", evento_id="evt1")
    assert t.padrao is False
    assert t.valor is None
