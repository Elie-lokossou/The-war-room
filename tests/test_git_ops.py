import pytest
import os
from lib.git_ops import get_commit_url, commit_postmortem

def test_get_commit_url():
    url = get_commit_url("abc1234")
    assert "abc1234" in url
    assert "github.com" in url

def test_commit_postmortem_fallback(tmp_path):
    # Test commit_postmortem writes the markdown report.
    # Note: since the repo root is determined in relation to the file path of git_ops.py,
    # it will write under the actual repo's postmortems directory.
    # Let's write a temporary postmortem and check if the file exists.
    incident_id = "test-temp-pm"
    md_content = "# Test Postmortem Content"
    
    success, commit_hash = commit_postmortem(incident_id, md_content)
    assert success
    
    # Verify the file was written
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    expected_file = os.path.join(repo_root, "postmortems", f"inc-{incident_id}", "postmortem.md")
    assert os.path.exists(expected_file)
    with open(expected_file, "r") as f:
        assert f.read() == md_content
        
    # Clean up the test file and directory
    if os.path.exists(expected_file):
        os.remove(expected_file)
    expected_dir = os.path.dirname(expected_file)
    if os.path.exists(expected_dir):
        os.rmdir(expected_dir)
