"""Three real catalog photographs -> saved teacher edits -> normalized sprites.
Use --backend qwen on a CUDA worker to repeat generation with the open model.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aquarium.cli import main
main(['sprites', *sys.argv[1:]])
