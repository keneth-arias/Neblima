"""Generar seis pronósticos en µg/m³ desde los pesos guardados de la red convolucional."""

import argparse
from pathlib import Path

from compare_cnn import predict_from_checkpoint

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("windows", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--batch", type=int, default=16)
    predict_from_checkpoint(**vars(parser.parse_args()))
