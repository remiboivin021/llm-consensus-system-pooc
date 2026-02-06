import json

import src.core.scoring.engine as eng


def test_extract_code_handles_nested_files():
    payload = json.dumps(
        {
            "files": [
                {"filename": "a", "code": ""},
                {"filename": "b", "code": "print('b')"},
            ]
        }
    )
    # Because first file code is empty, extractor should still fall through to next non-empty code.
    assert "print('b')" in eng._extract_code(payload)


def test_extract_code_uses_markdown_block_when_json_empty():
    content = """{
      "files": []
    }

    ```python
    def hello():
        return 'world'
    ```
    """
    assert "def hello" in eng._extract_code(content)
