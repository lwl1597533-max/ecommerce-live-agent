import asyncio
import pytest
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage
from app import chains
from app.config import settings
from app.models import Product, SellingPointResult

def test_structured_retry(monkeypatch):
    calls=[]
    valid=SellingPointResult(product_id='x', summary='sample', selling_points=[{'point':str(i),'evidence':'source','target_user':'buyers','priority':i} for i in range(1,4)])
    def respond(prompt):
        calls.append(prompt)
        return AIMessage(content='not-json' if len(calls)==1 else valid.model_dump_json())
    monkeypatch.setattr(chains,'llm',lambda style:RunnableLambda(respond))
    result=asyncio.run(chains.structured('Extract',{'name':'sample'},SellingPointResult))
    assert result.product_id=='x'
    assert len(calls)==2

def test_cache_separates_models(monkeypatch):
    product=Product(product_id='x',name='name',category='test',price=1,description='test')
    before=chains.storage.key(product)
    monkeypatch.setattr(settings,'model_name','different-model')
    assert before!=chains.storage.key(product)

def test_provider_failure_is_not_json_retry(monkeypatch):
    calls=[]
    def respond(prompt):
        calls.append(prompt)
        return AIMessage(content='模型请求失败，请稍后重试或更换模型。')
    monkeypatch.setattr(chains,'llm',lambda style:RunnableLambda(respond))
    with pytest.raises(chains.ModelUnavailableError):
        asyncio.run(chains.structured('Extract',{},SellingPointResult))
    assert len(calls)==1
