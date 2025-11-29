#!/bin/bash
# Setup script for Ollama on MacBook Pro
# This script installs Ollama and downloads recommended models for FX sentiment analysis

set -e

echo "=========================================="
echo "Ollama Setup for FX-AI Advisor"
echo "=========================================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  This script is designed for macOS (MacBook Pro)"
    echo "For other platforms, visit: https://ollama.ai"
    exit 1
fi

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is already installed"
    ollama --version
else
    echo "📦 Installing Ollama..."
    echo ""
    echo "Please download and install Ollama from:"
    echo "https://ollama.ai/download"
    echo ""
    echo "After installation, run this script again."
    exit 0
fi

echo ""
echo "=========================================="
echo "Available Models for FX Sentiment Analysis"
echo "=========================================="
echo ""
echo "1. llama3:8b (4.7GB) - RECOMMENDED"
echo "   - Best balance of speed and quality"
echo "   - Excellent for structured JSON output"
echo "   - ~2-5 seconds per analysis on M1/M2"
echo ""
echo "2. mistral:7b (4.1GB) - FAST"
echo "   - Very fast inference"
echo "   - Good quality"
echo "   - ~1-3 seconds per analysis"
echo ""
echo "3. phi3:mini (2.3GB) - FASTEST"
echo "   - Smallest model"
echo "   - Fastest inference"
echo "   - ~1-2 seconds per analysis"
echo ""
echo "4. gemma:7b (5.0GB) - GOOD"
echo "   - Google's Gemma model"
echo "   - Good for structured output"
echo "   - ~2-4 seconds per analysis"
echo ""
echo "5. qwen2:7b (4.4GB) - EXCELLENT"
echo "   - Strong reasoning capabilities"
echo "   - Excellent quality"
echo "   - ~2-5 seconds per analysis"
echo ""

# Ask user which model to install
echo "Which model would you like to install?"
echo "Enter number (1-5) or 'all' to install all models:"
read -r choice

case $choice in
    1)
        echo "📥 Downloading llama3:8b..."
        ollama pull llama3:8b
        MODEL="llama3"
        ;;
    2)
        echo "📥 Downloading mistral:7b..."
        ollama pull mistral:7b
        MODEL="mistral"
        ;;
    3)
        echo "📥 Downloading phi3:mini..."
        ollama pull phi3:mini
        MODEL="phi3"
        ;;
    4)
        echo "📥 Downloading gemma:7b..."
        ollama pull gemma:7b
        MODEL="gemma"
        ;;
    5)
        echo "📥 Downloading qwen2:7b..."
        ollama pull qwen2:7b
        MODEL="qwen2"
        ;;
    all)
        echo "📥 Downloading all models (this will take a while)..."
        ollama pull llama3:8b
        ollama pull mistral:7b
        ollama pull phi3:mini
        ollama pull gemma:7b
        ollama pull qwen2:7b
        MODEL="llama3"
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "✓ Model(s) downloaded successfully!"
echo ""

# List installed models
echo "=========================================="
echo "Installed Models:"
echo "=========================================="
ollama list

echo ""
echo "=========================================="
echo "Configuration"
echo "=========================================="
echo ""
echo "Update your .env file with:"
echo ""
echo "LLM_PROVIDER=ollama"
echo "OLLAMA_MODEL=$MODEL"
echo "OLLAMA_BASE_URL=http://localhost:11434"
echo ""

# Test the model
echo "=========================================="
echo "Testing Model"
echo "=========================================="
echo ""
echo "Running a quick test..."
echo ""

ollama run $MODEL "Respond with just 'OK' if you can understand this message." --verbose=false

echo ""
echo "=========================================="
echo "Setup Complete! 🎉"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update .env: LLM_PROVIDER=ollama"
echo "2. Update .env: OLLAMA_MODEL=$MODEL"
echo "3. Run: make news-ingester"
echo ""
echo "💡 Tips:"
echo "- Ollama runs in the background automatically"
echo "- Models are cached locally (no internet needed after download)"
echo "- Zero API costs! 🆓"
echo "- Performance: ~2-5 seconds per news analysis on M1/M2"
echo ""
echo "📚 Documentation:"
echo "- Ollama: https://ollama.ai/library"
echo "- FX-AI Docs: docs/OLLAMA_SETUP.md"
echo ""
