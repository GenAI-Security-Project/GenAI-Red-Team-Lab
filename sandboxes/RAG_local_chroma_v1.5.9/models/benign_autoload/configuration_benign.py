"""Minimal config class for the benign autoload test model."""

from transformers import PretrainedConfig


class BenignConfig(PretrainedConfig):
    model_type = "benign_autoload"
