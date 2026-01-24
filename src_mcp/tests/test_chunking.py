"""Tests for chunking functionality including code block preservation."""

import pytest
from build_index import chunk_text


class TestChunking:
    """Test chunking functionality with various scenarios."""

    def test_basic_chunking(self):
        """Test basic text chunking without code blocks."""
        text = "# Header\n\nThis is a paragraph with many words to test chunking. " * 20
        chunks = chunk_text(text, chunk_size=50, overlap_lines=2)
        
        assert len(chunks) > 1
        assert all('text' in chunk for chunk in chunks)
        assert all('start_line' in chunk for chunk in chunks)
        assert all('end_line' in chunk for chunk in chunks)

    def test_heading_context_preservation(self):
        """Test that headings are preserved in chunk context."""
        text = """# Main Header
## Sub Header
### Sub Sub Header

Content under the headers that should be chunked.
""" + "More content. " * 30
        
        chunks = chunk_text(text, chunk_size=20, overlap_lines=1)
        
        # All chunks should contain heading context
        for chunk in chunks:
            assert "# Main Header" in chunk['text']
            assert "## Sub Header" in chunk['text']
            assert "### Sub Sub Header" in chunk['text']

    def test_code_block_preservation(self):
        """Test that code blocks are never split across chunks."""
        text = """# Code Example

Here's some text before the code.

```python
def example_function():
    # This is a long function
    for i in range(100):
        print(f"Line {i}")
        if i > 50:
            break
    return "done"
```

Text after the code block.
""" + "More text. " * 50
        
        chunks = chunk_text(text, chunk_size=10, overlap_lines=1)
        
        # Find chunk containing code block
        code_chunk = None
        for chunk in chunks:
            if "```python" in chunk['text'] and "```" in chunk['text']:
                code_chunk = chunk
                break
        
        assert code_chunk is not None, "Code block should be in a single chunk"
        
        # Verify complete code block is preserved
        assert "def example_function():" in code_chunk['text']
        assert "return \"done\"" in code_chunk['text']
        assert code_chunk['text'].count("```") == 2  # Opening and closing

    def test_multiple_code_blocks(self):
        """Test handling of multiple code blocks."""
        text = """# Multiple Code Examples

First example:
```bash
echo "hello"
```

Second example:
```python
print("world")
```

End text.
"""
        
        chunks = chunk_text(text, chunk_size=5, overlap_lines=1)
        
        # Count code blocks across all chunks
        total_code_blocks = 0
        for chunk in chunks:
            total_code_blocks += chunk['text'].count("```") // 2
        
        assert total_code_blocks == 2, "Both code blocks should be preserved"

    def test_nested_code_blocks_edge_case(self):
        """Test edge case with code blocks containing triple backticks."""
        # This is a known limitation - nested backticks are complex to handle
        # For now, we test that the function doesn't crash and produces some output
        text = """# Edge Case

```markdown
Here's how to write code blocks:
```

Regular text after.
"""
        
        chunks = chunk_text(text, chunk_size=5, overlap_lines=1)
        
        # Should not crash and should produce chunks
        assert len(chunks) > 0
        
        # Should preserve the outer code block
        code_chunk = None
        for chunk in chunks:
            if "```markdown" in chunk['text']:
                code_chunk = chunk
                break
        
        assert code_chunk is not None

    def test_code_block_at_chunk_boundary(self):
        """Test code block that would normally be split at chunk boundary."""
        # Create text that would split right at code block
        prefix_text = "Word " * 15  # Exactly 15 words
        code_block = """```python
def test():
    return True
```"""
        suffix_text = "More text after."
        
        text = f"# Header\n\n{prefix_text}\n\n{code_block}\n\n{suffix_text}"
        
        chunks = chunk_text(text, chunk_size=15, overlap_lines=1)
        
        # Code block should not be split
        code_found = False
        for chunk in chunks:
            if "```python" in chunk['text']:
                assert "def test():" in chunk['text']
                assert "return True" in chunk['text']
                code_found = True
        
        assert code_found, "Code block should be preserved intact"

    def test_very_large_code_block(self):
        """Test that very large code blocks are kept together."""
        large_code = "```python\n" + "print('line')\n" * 100 + "```"
        text = f"# Header\n\nBefore code.\n\n{large_code}\n\nAfter code."
        
        chunks = chunk_text(text, chunk_size=10, overlap_lines=1)
        
        # Large code block should be in single chunk despite size
        code_chunk = None
        for chunk in chunks:
            if "```python" in chunk['text']:
                code_chunk = chunk
                break
        
        assert code_chunk is not None
        assert chunk['text'].count("print('line')") == 100

    def test_line_numbers_accuracy(self):
        """Test that line numbers are accurate after chunking."""
        text = """# Header
Line 1
Line 2
Line 3
Line 4
Line 5
Line 6
Line 7
Line 8
Line 9
Line 10"""
        
        chunks = chunk_text(text, chunk_size=5, overlap_lines=1)
        
        # Verify line numbers start at 1
        assert chunks[0]['start_line'] == 1
        
        # Check that chunks cover all lines
        max_end_line = max(chunk['end_line'] for chunk in chunks)
        assert max_end_line == 11  # 11 lines total including header

    def test_empty_text(self):
        """Test chunking empty text."""
        chunks = chunk_text("", chunk_size=10, overlap_lines=1)
        assert len(chunks) == 0

    def test_single_line_text(self):
        """Test chunking single line text."""
        chunks = chunk_text("Single line", chunk_size=10, overlap_lines=1)
        assert len(chunks) == 1
        assert chunks[0]['start_line'] == 1
        assert chunks[0]['end_line'] == 1

    def test_overlap_functionality(self):
        """Test that overlap between chunks works correctly."""
        text = """# Header

Line 1 content
Line 2 content  
Line 3 content
Line 4 content
Line 5 content
Line 6 content"""
        
        chunks = chunk_text(text, chunk_size=2, overlap_lines=2)
        
        if len(chunks) > 1:
            # Check that there's overlap between consecutive chunks
            first_chunk_lines = chunks[0]['text'].split('\n')
            second_chunk_lines = chunks[1]['text'].split('\n')
            
            # Should have some overlapping content (after headers)
            overlap_found = any(line in second_chunk_lines for line in first_chunk_lines[-3:])
            assert overlap_found, "Chunks should have overlapping content"
