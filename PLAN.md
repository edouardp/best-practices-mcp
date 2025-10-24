# Container Size Optimization Plan

## Current State
- ~~Container size: 1.96 GB~~
- **New container size: 1.77 GB** ✅
- **Space saved: 190 MB** ✅
- Virtual environment: ~~940 MB~~ → **Reduced**
- Main culprit: ~~Full transformers library with unused models~~ → **Fixed**
- Actually using: `sentence-transformers/all-mpnet-base-v2` model only

## ✅ COMPLETED: Option 1 - Direct Model Usage (Implemented)

**Changes made:**
- Replaced `sentence-transformers` with direct `transformers` + `torch`
- Updated `build_index.py` and `server.py` to use `AutoTokenizer` and `AutoModel`
- Created custom `encode_text()` function with mean pooling
- Updated `pyproject.toml` dependencies
- Regenerated `uv.lock` file
- Updated Dockerfile model pre-download step

**Results:**
- **Container size reduced from 1.96 GB to 1.77 GB**
- **Space savings: 190 MB (9.7% reduction)**
- Functionality preserved - all tests pass
- Same embedding quality maintained

## Remaining Optimization Options

### Option 2: ONNX Runtime (Future Enhancement)
```bash
pip install optimum[onnxruntime]
```
```python
from optimum.onnxruntime import ORTModelForFeatureExtraction
model = ORTModelForFeatureExtraction.from_pretrained('sentence-transformers/all-mpnet-base-v2', export=True)
```

**Expected additional savings: 200-300 MB + faster inference**

### Option 3: CPU-Only Torch (Future Enhancement)
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```
**Expected additional savings: 100-200 MB**

### Option 4: Multi-stage Docker Build (Already Implemented)
✅ Already using multi-stage build for optimal layer caching

## Files Modified
- ✅ `src/sdlc_mcp/build_index.py` - Direct transformers usage
- ✅ `src/sdlc_mcp/server.py` - Direct transformers usage  
- ✅ `pyproject.toml` - Updated dependencies
- ✅ `requirements.txt` - Updated dependencies
- ✅ `uv.lock` - Regenerated with new dependencies
- ✅ `Dockerfile` - Updated model pre-download step

## Next Steps (Optional)
1. Consider ONNX runtime for additional 200-300 MB savings
2. Evaluate CPU-only torch for additional 100-200 MB savings
3. Monitor for any performance differences in production
