# Ollama Setup Guide - Run LLMs Locally on MacBook Pro

## 🎯 Why Ollama?

**Run LLMs locally on your MacBook Pro with ZERO API costs!**

### Benefits
- ✅ **FREE**: No API costs, unlimited usage
- ✅ **FAST**: 2-5 seconds per analysis on M1/M2/M3
- ✅ **PRIVATE**: Data never leaves your machine
- ✅ **OFFLINE**: Works without internet (after model download)
- ✅ **POWERFUL**: Llama 3, Mistral, Phi-3, Gemma, Qwen2

### Comparison

| Provider | Cost/Month | Speed | Privacy | Offline |
|----------|------------|-------|---------|---------|
| **Ollama** | $0 | 2-5s | ✅ Local | ✅ Yes |
| OpenAI GPT-4 | $37.50 | 1-2s | ❌ Cloud | ❌ No |
| Anthropic Claude | $30 | 1-2s | ❌ Cloud | ❌ No |

---

## 🚀 Quick Start

### Step 1: Install Ollama

```bash
# Option 1: Download from website (recommended)
# Visit: https://ollama.ai/download
# Download and install Ollama.app

# Option 2: Use Homebrew
brew install ollama
```

### Step 2: Run Setup Script

```bash
# Automated setup
./scripts/setup_ollama.sh
```

This will:
1. Check if Ollama is installed
2. Show available models
3. Download your chosen model
4. Test the installation
5. Provide configuration instructions

### Step 3: Configure FX-AI

Edit `.env`:
```bash
# Change provider to ollama
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3
OLLAMA_BASE_URL=http://localhost:11434
```

### Step 4: Test It

```bash
# Test Ollama client
python scripts/test_ollama.py

# Run news ingester with Ollama
make news-ingester
```

---

## 📦 Recommended Models

### 1. Llama 3 8B (RECOMMENDED) ⭐

**Best for**: Production use, best quality

```bash
ollama pull llama3:8b
```

**Specs**:
- Size: 4.7GB
- Speed: 2-5 seconds per analysis
- Quality: Excellent
- RAM: 8GB recommended

**Why choose this**:
- Best balance of speed and quality
- Excellent at structured JSON output
- Strong reasoning capabilities
- Developed by Meta AI

**Performance on MacBook Pro**:
- M1: ~4-5 seconds
- M2: ~3-4 seconds
- M3: ~2-3 seconds

---

### 2. Mistral 7B (FAST) ⚡

**Best for**: High-volume processing, speed priority

```bash
ollama pull mistral:7b
```

**Specs**:
- Size: 4.1GB
- Speed: 1-3 seconds per analysis
- Quality: Good
- RAM: 8GB recommended

**Why choose this**:
- Fastest among 7B models
- Good quality for most tasks
- Efficient memory usage

---

### 3. Phi-3 Mini (FASTEST) 🚀

**Best for**: Maximum speed, resource-constrained

```bash
ollama pull phi3:mini
```

**Specs**:
- Size: 2.3GB
- Speed: 1-2 seconds per analysis
- Quality: Good
- RAM: 4GB minimum

**Why choose this**:
- Smallest model
- Fastest inference
- Works on older MacBooks
- Developed by Microsoft

---

### 4. Gemma 7B (STRUCTURED) 📊

**Best for**: Structured output, JSON reliability

```bash
ollama pull gemma:7b
```

**Specs**:
- Size: 5.0GB
- Speed: 2-4 seconds per analysis
- Quality: Good
- RAM: 8GB recommended

**Why choose this**:
- Excellent at structured output
- Reliable JSON formatting
- Developed by Google

---

### 5. Qwen2 7B (REASONING) 🧠

**Best for**: Complex analysis, reasoning tasks

```bash
ollama pull qwen2:7b
```

**Specs**:
- Size: 4.4GB
- Speed: 2-5 seconds per analysis
- Quality: Excellent
- RAM: 8GB recommended

**Why choose this**:
- Strong reasoning capabilities
- Excellent for financial analysis
- Developed by Alibaba

---

## 💻 System Requirements

### Minimum Requirements
- **MacBook**: M1, M2, or M3 chip
- **RAM**: 8GB (16GB recommended)
- **Storage**: 5-10GB free space per model
- **macOS**: 12.0 (Monterey) or later

### Recommended Setup
- **MacBook Pro**: M1 Pro/Max, M2 Pro/Max, or M3 Pro/Max
- **RAM**: 16GB or more
- **Storage**: 20GB+ free space
- **macOS**: Latest version

### Performance by Mac Model

| Mac Model | Llama 3 8B | Mistral 7B | Phi-3 Mini |
|-----------|------------|------------|------------|
| **M1** | 4-5s | 2-3s | 1-2s |
| **M1 Pro** | 3-4s | 2s | 1s |
| **M1 Max** | 2-3s | 1-2s | <1s |
| **M2** | 3-4s | 2s | 1s |
| **M2 Pro** | 2-3s | 1-2s | <1s |
| **M2 Max** | 2s | 1s | <1s |
| **M3** | 2-3s | 1-2s | <1s |
| **M3 Pro** | 2s | 1s | <1s |
| **M3 Max** | 1-2s | <1s | <1s |

---

## 🔧 Advanced Configuration

### Custom Ollama Settings

```bash
# .env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_TIMEOUT=30  # Increase for slower Macs

# Temperature (0.0-1.0)
LLM_TEMPERATURE=0.3  # Lower = more consistent

# Max tokens
LLM_MAX_TOKENS=1000  # Reduce for faster inference
```

### Multiple Models

You can install multiple models and switch between them:

```bash
# Install multiple models
ollama pull llama3:8b
ollama pull mistral:7b
ollama pull phi3:mini

# Switch in .env
OLLAMA_MODEL=llama3    # For quality
OLLAMA_MODEL=mistral   # For speed
OLLAMA_MODEL=phi3      # For efficiency
```

### Model Variants

Some models have multiple sizes:

```bash
# Llama 3
ollama pull llama3:8b      # 4.7GB - Recommended
ollama pull llama3:70b     # 40GB - Best quality (requires 64GB RAM)

# Mistral
ollama pull mistral:7b     # 4.1GB - Standard
ollama pull mistral:7b-instruct  # Instruction-tuned

# Phi-3
ollama pull phi3:mini      # 2.3GB - Smallest
ollama pull phi3:medium    # 7.9GB - Better quality
```

---

## 🧪 Testing

### Test Ollama Installation

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# List installed models
ollama list

# Test a model
ollama run llama3 "Hello, can you analyze FX news?"
```

### Test with FX-AI

Create `scripts/test_ollama.py`:

```python
import asyncio
from datetime import datetime, timezone
from apps.llm.ollama_client import OllamaClient, check_ollama_available, list_ollama_models

async def test_ollama():
    # Check if Ollama is available
    if not check_ollama_available():
        print("❌ Ollama is not running")
        print("Start Ollama: ollama serve")
        return
    
    print("✓ Ollama is running")
    
    # List models
    models = list_ollama_models()
    print(f"✓ Available models: {', '.join(models)}")
    
    # Test sentiment analysis
    client = OllamaClient(model="llama3")
    
    result = await client.analyze_sentiment(
        headline="Fed Raises Rates by 25bps",
        content="The Federal Reserve raised interest rates by 25 basis points today...",
        source="test",
        timestamp=datetime.now(timezone.utc)
    )
    
    print(f"\n✓ Sentiment analysis complete:")
    print(f"  Sentiment USD: {result.sentiment_usd:+.2f}")
    print(f"  Impact: {result.impact_score:.1f}/10")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Processing time: {result.processing_time_ms}ms")
    print(f"  Cost: ${result.api_cost_usd:.4f} (FREE!)")

asyncio.run(test_ollama())
```

Run:
```bash
python scripts/test_ollama.py
```

---

## 📊 Performance Optimization

### 1. Reduce Model Size

Use smaller models for faster inference:

```bash
# Instead of llama3:8b (4.7GB)
ollama pull phi3:mini  # 2.3GB, 2x faster
```

### 2. Adjust Token Limits

```bash
# .env
LLM_MAX_TOKENS=500  # Reduce from 1000 for faster inference
```

### 3. Batch Processing

Process multiple news items in parallel:

```bash
# .env
NEWS_SENTIMENT_BATCH_SIZE=3  # Process 3 at a time
```

### 4. Increase Timeout

For slower Macs:

```bash
# .env
OLLAMA_TIMEOUT=60  # Increase from 30 seconds
```

### 5. Close Other Apps

Free up RAM for better performance:
- Close Chrome/Safari tabs
- Quit unused applications
- Monitor Activity Monitor

---

## 💰 Cost Comparison

### Monthly Costs (100 news items/day)

| Provider | Model | Cost/Month | Speed |
|----------|-------|------------|-------|
| **Ollama** | Llama 3 8B | **$0** | 3-5s |
| **Ollama** | Mistral 7B | **$0** | 2-3s |
| **Ollama** | Phi-3 Mini | **$0** | 1-2s |
| OpenAI | GPT-4 Turbo | $75 | 1-2s |
| OpenAI | GPT-3.5 Turbo | $7.50 | 1s |
| Anthropic | Claude 3 Opus | $90 | 1-2s |
| Anthropic | Claude 3 Sonnet | $22.50 | 1s |

### Annual Savings

**Ollama vs OpenAI GPT-4**:
- OpenAI: $75/month × 12 = **$900/year**
- Ollama: **$0/year**
- **Savings: $900/year** 💰

**Ollama vs Claude 3 Sonnet**:
- Claude: $22.50/month × 12 = **$270/year**
- Ollama: **$0/year**
- **Savings: $270/year** 💰

---

## 🐛 Troubleshooting

### Issue: Ollama not found

**Error**: `command not found: ollama`

**Solution**:
```bash
# Install Ollama
brew install ollama
# Or download from https://ollama.ai/download
```

### Issue: Connection refused

**Error**: `Connection refused to localhost:11434`

**Solution**:
```bash
# Start Ollama service
ollama serve

# Or restart Ollama app
# Applications → Ollama → Quit
# Applications → Ollama → Open
```

### Issue: Model not found

**Error**: `model 'llama3' not found`

**Solution**:
```bash
# Download the model
ollama pull llama3:8b

# Verify it's installed
ollama list
```

### Issue: Slow performance

**Symptoms**: >10 seconds per analysis

**Solutions**:
1. **Use smaller model**:
   ```bash
   ollama pull phi3:mini
   # Update .env: OLLAMA_MODEL=phi3
   ```

2. **Reduce token limit**:
   ```bash
   # .env: LLM_MAX_TOKENS=500
   ```

3. **Close other apps**: Free up RAM

4. **Check Activity Monitor**: Ensure Ollama isn't CPU-throttled

### Issue: Out of memory

**Error**: `failed to allocate memory`

**Solutions**:
1. **Use smaller model**: phi3:mini (2.3GB)
2. **Close other apps**: Free up RAM
3. **Restart Mac**: Clear memory leaks
4. **Upgrade RAM**: Consider 16GB+ for best performance

### Issue: JSON parsing errors

**Error**: `no_json_found_in_response`

**Solutions**:
1. **Try different model**: Gemma is best for structured output
2. **Increase timeout**: `OLLAMA_TIMEOUT=60`
3. **Check model**: Ensure it's instruction-tuned

---

## 🎯 Best Practices

### 1. Start with Llama 3

```bash
ollama pull llama3:8b
```

Best balance of quality and speed.

### 2. Monitor Performance

```bash
# Check processing time in logs
make tail-sentiment | grep processing_time_ms
```

### 3. Use Caching

```bash
# .env
LLM_CACHE_TTL_SECONDS=300  # Cache for 5 minutes
```

### 4. Batch Processing

```bash
# Process multiple items together
NEWS_SENTIMENT_BATCH_SIZE=5
```

### 5. Regular Updates

```bash
# Update Ollama
brew upgrade ollama

# Update models
ollama pull llama3:8b
```

---

## 🔗 Resources

- **Ollama Website**: https://ollama.ai
- **Ollama GitHub**: https://github.com/ollama/ollama
- **Model Library**: https://ollama.ai/library
- **Llama 3**: https://ollama.ai/library/llama3
- **Mistral**: https://ollama.ai/library/mistral
- **Phi-3**: https://ollama.ai/library/phi3

---

## 🎉 Summary

**Ollama on MacBook Pro**:
- ✅ **FREE**: Zero API costs
- ✅ **FAST**: 2-5 seconds per analysis
- ✅ **PRIVATE**: Data stays local
- ✅ **POWERFUL**: Llama 3, Mistral, Phi-3
- ✅ **EASY**: One command setup

**Get started now**:
```bash
./scripts/setup_ollama.sh
```

**Save $900/year compared to GPT-4!** 💰

---

**Questions?** Check the main documentation or create an issue on GitHub.
