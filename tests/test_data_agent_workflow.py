import asyncio
from types import SimpleNamespace
import pytest
from src.agents import data_agent as agent

class FakeLLM:
    def __init__(self, content='Zusammenfassung', metadata=None, error=False, delay=0):
        self.content, self.metadata, self.error, self.delay = content, metadata or {}, error, delay
        self.calls = 0
    async def ainvoke(self, messages):
        self.calls += 1
        await asyncio.sleep(self.delay)
        if self.error:
            raise RuntimeError('secret provider error')
        return SimpleNamespace(content=self.content, response_metadata=self.metadata,
                               usage_metadata={'input_tokens': 10, 'output_tokens': 4})

def execute(monkeypatch, tmp_path, fake, text='## Name\nTestfirma', timeout=2):
    document = tmp_path / 'company.md'
    document.write_text(text, encoding='utf-8')
    monkeypatch.setattr(agent, 'ALLOWED_FILE', document)
    monkeypatch.setattr(agent, 'get_chat_model', lambda **kwargs: fake)
    return asyncio.run(agent.run_data_agent(agent.DataTask(task_id='test', timeout_seconds=timeout),
                                           trace_file=str(tmp_path / 'trace.jsonl')))

def test_success_and_trace(monkeypatch, tmp_path):
    import json
    fake = FakeLLM()
    result = execute(monkeypatch, tmp_path, fake)
    assert result['status'] == 'success' and fake.calls == 1
    trace = json.loads((tmp_path / 'trace.jsonl').read_text())
    assert trace['calls'] == 1 and trace['input_tokens'] == 10
    assert trace['tools'] == ['read_project_document']

@pytest.mark.parametrize('fake', [FakeLLM(''), FakeLLM([]), FakeLLM('text', {'done_reason': 'length'}),
                                 FakeLLM('text', {'finish_reason': 'length'}), FakeLLM(error=True)])
def test_bad_response(monkeypatch, tmp_path, fake):
    result = execute(monkeypatch, tmp_path, fake)
    assert result['status'] == 'error' and result['summary'] == ''
    assert 'secret' not in result['error']

@pytest.mark.parametrize('text', ['', 'x' * 12001])
def test_reader_failure_skips_model(monkeypatch, tmp_path, text):
    fake = FakeLLM()
    assert execute(monkeypatch, tmp_path, fake, text)['status'] == 'error'
    assert fake.calls == 0

def test_deadline(monkeypatch, tmp_path):
    result = execute(monkeypatch, tmp_path, FakeLLM(delay=1), timeout=0.02)
    assert result['status'] == 'error' and 'Gesamtzeitlimit' in result['error']

def test_contract():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        agent.DataTask(task_id='', timeout_seconds=0)

def test_adapter_reasoning():
    from src.llm.factory import get_chat_model
    from src.app.settings import Settings
    model = get_chat_model(Settings(_env_file=None), reasoning=False)
    assert model._chat_params([])['think'] is False

def test_reasoning_is_not_summary(monkeypatch, tmp_path):
    result = execute(monkeypatch, tmp_path, FakeLLM('<think>internal</think>'))
    assert result['status'] == 'error' and result['summary'] == ''

def test_invalid_success_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        agent.DataResult(status='success', summary='')

def test_openai_adapter_does_not_send_ollama_option():
    from src.llm.factory import get_chat_model
    from src.app.settings import Settings
    model = get_chat_model(Settings(_env_file=None, llm_provider='openai_compatible'), reasoning=False)
    assert 'reasoning' not in model.model_kwargs
    assert model.max_retries == 0

def test_missing_document_graph_skips_model(monkeypatch, tmp_path):
    fake = FakeLLM()
    monkeypatch.setattr(agent, 'ALLOWED_FILE', tmp_path / 'missing.md')
    monkeypatch.setattr(agent, 'get_chat_model', lambda **kwargs: fake)
    state = asyncio.run(agent.build_graph().ainvoke({}))
    assert state['status'] == 'error' and state['error']
    assert fake.calls == 0

def test_invalid_utf8_graph_skips_model(monkeypatch, tmp_path):
    document = tmp_path / 'company.md'
    document.write_bytes(b'\xff')
    monkeypatch.setattr(agent, 'ALLOWED_FILE', document)
    fake = FakeLLM()
    monkeypatch.setattr(agent, 'get_chat_model', lambda **kwargs: fake)
    state = asyncio.run(agent.build_graph().ainvoke({}))
    assert state['status'] == 'error' and fake.calls == 0

def test_chunks_have_source_and_bound(monkeypatch, tmp_path):
    document = tmp_path / 'company.md'
    document.write_text('## Long\n' + 'x' * 4500, encoding='utf-8')
    monkeypatch.setattr(agent, 'ALLOWED_FILE', document)
    result = agent.read_project_document()
    assert result['chunk_count'] == 3
    assert all(len(chunk['text']) <= 2000 for chunk in result['chunks'])
    assert all(chunk['source'] == result['source'] for chunk in result['chunks'])
