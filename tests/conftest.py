import pytest
from industrialdata.generate import generate
from industrialdata.run import execute,current_snapshot

@pytest.fixture(scope='module')
def demo(tmp_path_factory):
    folder=tmp_path_factory.mktemp('demo')
    generate(folder,minutes=420,offline=True)
    report=execute(folder,offline=True)
    return folder,report,current_snapshot(folder)
