"""Shared helpers for the Streamlit app and the web API."""
from .config import MODEL_PATH, SAMPLE_DATA_PATH
from .data import load_sites_csv, make_sample_dataset
from .model import DemandRangeModel


def get_model():
    """Load the saved model, or train a quick simulated one if none exists."""
    if MODEL_PATH.exists():
        return DemandRangeModel.load(MODEL_PATH)
    df = load_sites_csv(SAMPLE_DATA_PATH) if SAMPLE_DATA_PATH.exists() else make_sample_dataset()
    model = DemandRangeModel().fit(df)
    model.meta["data_source"] = "simulated"
    try:
        model.save(MODEL_PATH)
    except OSError:
        pass
    return model


def model_info(model):
    """What the model learned from. The front end must show this honestly."""
    src = model.meta.get("data_source", "unknown")
    simulated = src in ("simulated", "unknown")
    return {
        "data_source": src,
        "trained_on_simulated_data": simulated,
        "n_sites": model.meta.get("n_sites"),
        "n_rows": model.meta.get("n_rows"),
        "small_data": bool(model.meta.get("small_data")),
        "warning": ("This model was trained on SIMULATED villages. Numbers show how "
                    "the method works, not what a real site will do.") if simulated else
                   (f"Trained on only {model.meta.get('n_sites')} real sites. Treat the range as indicative."
                    if model.meta.get("small_data") else None),
    }
