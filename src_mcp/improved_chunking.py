def chunk_text_preserve_code_blocks(text: str, chunk_size: int = 150, overlap_lines: int = 5) -> List[Dict]:
    """
    Split markdown text into overlapping chunks while preserving code blocks.
    
    Key improvement: Never splits inside fenced code blocks (```...```)
    """
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_words = 0
    start_line = 1
    current_line = 1
    
    # Track current heading hierarchy
    current_headings = {'h1': '', 'h2': '', 'h3': ''}
    overlap_buffer = []
    
    # Track code block state
    in_code_block = False
    
    for line in lines:
        # Update heading context
        if line.startswith('# '):
            current_headings['h1'] = line
            current_headings['h2'] = ''
            current_headings['h3'] = ''
        elif line.startswith('## '):
            current_headings['h2'] = line
            current_headings['h3'] = ''
        elif line.startswith('### '):
            current_headings['h3'] = line
        
        # Track code block boundaries
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
        
        words = line.split()
        
        # Only chunk if we're NOT in a code block and size limit reached
        if (current_words + len(words) > chunk_size and 
            current_chunk and 
            not in_code_block):
            
            # Build chunk with heading context
            heading_context = []
            if current_headings['h1']:
                heading_context.append(current_headings['h1'])
            if current_headings['h2']:
                heading_context.append(current_headings['h2'])
            if current_headings['h3']:
                heading_context.append(current_headings['h3'])
            
            chunk_with_context = heading_context + [''] + current_chunk
            
            chunks.append({
                'text': '\n'.join(chunk_with_context),
                'start_line': start_line,
                'end_line': current_line - 1
            })
            
            # Prepare overlap for next chunk
            overlap_buffer = (current_chunk[-overlap_lines:] 
                            if len(current_chunk) >= overlap_lines 
                            else current_chunk)
            
            current_chunk = overlap_buffer.copy()
            current_words = sum(len(l.split()) for l in current_chunk)
            start_line = current_line - len(overlap_buffer)
        
        current_chunk.append(line)
        current_words += len(words)
        current_line += 1
    
    # Handle final chunk
    if current_chunk:
        heading_context = []
        if current_headings['h1']:
            heading_context.append(current_headings['h1'])
        if current_headings['h2']:
            heading_context.append(current_headings['h2'])
        if current_headings['h3']:
            heading_context.append(current_headings['h3'])
        
        chunk_with_context = heading_context + [''] + current_chunk
        
        chunks.append({
            'text': '\n'.join(chunk_with_context),
            'start_line': start_line,
            'end_line': current_line - 1
        })
    
    return chunks
