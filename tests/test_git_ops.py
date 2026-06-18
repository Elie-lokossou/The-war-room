import pytest
import os
from unittest.mock import patch, MagicMock
import subprocess
from lib.git_ops import get_commit_url, commit_postmortem

@patch("lib.git_ops.subprocess.run")
def test_get_commit_url(mock_run):
    # Test with successful git remote retrieval
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "git@github.com:vib3withsimran/The-war-room.git\n"
    mock_run.return_value = mock_res
    
    url = get_commit_url("abc1234")
    assert url == "https://github.com/vib3withsimran/The-war-room/commit/abc1234"
    
    # Test with failed git remote retrieval (fallback)
    mock_res.returncode = 1
    url = get_commit_url("abc1234")
    assert url == "https://github.com/vib3withsimran/The-war-room/commit/abc1234"

@patch("lib.git_ops.subprocess.run")
def test_commit_postmortem_success(mock_run):
    # Mock subprocess.run for git status, add, commit, rev-parse
    mock_status = MagicMock()
    mock_status.returncode = 0
    
    mock_add = MagicMock()
    mock_add.returncode = 0
    
    mock_commit = MagicMock()
    mock_commit.returncode = 0
    
    mock_hash = MagicMock()
    mock_hash.returncode = 0
    mock_hash.stdout = "mocked12\n"
    
    mock_run.side_effect = [mock_status, mock_add, mock_commit, mock_hash]
    
    incident_id = "test-temp-pm-success"
    md_content = "# Test Postmortem Content Success"
    
    success, commit_hash = commit_postmortem(incident_id, md_content)
    assert success
    assert commit_hash == "mocked12"
    
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

@patch("lib.git_ops.subprocess.run")
def test_commit_postmortem_fallback(mock_run):
    # Mock git status to fail (returncode != 0) to trigger fallback
    mock_status = MagicMock()
    mock_status.returncode = 1
    mock_run.return_value = mock_status
    
    incident_id = "test-temp-pm-fallback"
    md_content = "# Test Postmortem Content Fallback"
    
    success, commit_hash = commit_postmortem(incident_id, md_content)
    assert success
    assert commit_hash == ""
    
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

