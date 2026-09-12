from typing import cast

import lightning.pytorch as pl
import pandas as pd
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from pytorch_forecasting import QuantileLoss, TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer


def build_tft_dataloaders(
    csv_path: str, max_prediction_length: int = 5, max_encoder_length: int = 14
):
    """
    Constructs PyTorch data loaders, separating static vulnerabilities from dynamic weather.
    """
    df = pd.read_csv(csv_path)

    # Cast WARD to string to prevent GroupNormalizer integer errors
    df["WARD"] = df["WARD"].astype(str)

    # Reserve the final days for the validation/prediction window
    training_cutoff = df["time_idx"].max() - max_prediction_length
    training_df = df[df["time_idx"] <= training_cutoff].copy()

    training_dataset = TimeSeriesDataSet(
        training_df,
        time_idx="time_idx",
        target="Human_Stress_Index",
        group_ids=["WARD"],
        min_encoder_length=max_encoder_length // 2,
        max_encoder_length=max_encoder_length,
        min_prediction_length=1,
        max_prediction_length=max_prediction_length,
        # Static Demographics & Micro-climate (Constant per ward)
        static_categoricals=["WARD"],
        static_reals=[
            "Pop_Density_per_sqkm",
            "Elderly_Percent",
            "Outdoor_Worker_Percent",
            "NDVI",
            "NDBI",
            "LST_Celsius",
        ],
        # Known Future (Time progression)
        time_varying_known_reals=["time_idx"],
        # Unknown Future (Meteorological variables & Target)
        time_varying_unknown_reals=[
            "wind_speed_m_s",
            "solar_rad_W_m2",
            "RH_percent",
            "Localized_Ta",
            "WBGT_Celsius",
            "Human_Stress_Index",
        ],
        target_normalizer=GroupNormalizer(groups=["WARD"], transformation="softplus"),
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )

    validation_dataset = TimeSeriesDataSet.from_dataset(
        training_dataset, df, predict=True, stop_randomization=True
    )

    # Instantiate DataLoaders
    train_dataloader = training_dataset.to_dataloader(train=True, batch_size=64, num_workers=0)
    val_dataloader = validation_dataset.to_dataloader(train=False, batch_size=128, num_workers=0)

    return training_dataset, train_dataloader, val_dataloader


def initialize_heat_forecaster(training_dataset: TimeSeriesDataSet) -> TemporalFusionTransformer:
    """
    Initializes the model architecture to predict best, expected, and worst-case scenarios.
    """
    return cast(
        TemporalFusionTransformer,
        TemporalFusionTransformer.from_dataset(
            training_dataset,
            learning_rate=0.03,
            hidden_size=32,
            attention_head_size=4,
            dropout=0.1,
            hidden_continuous_size=16,
            # 10th percentile, Median, and 90th percentile predictions
            loss=QuantileLoss(quantiles=[0.1, 0.5, 0.9]),
            reduce_on_plateau_patience=4,
        ),
    )


def execute_tft_training(csv_path: str) -> str:
    """
    Master function to run the hardware-accelerated PyTorch Lightning trainer.
    """
    dataset, train_loader, val_loader = build_tft_dataloaders(csv_path)
    model = initialize_heat_forecaster(dataset)

    early_stop_callback = EarlyStopping(
        monitor="val_loss", min_delta=1e-4, patience=5, verbose=False, mode="min"
    )
    checkpoint_callback = ModelCheckpoint(monitor="val_loss", mode="min", save_top_k=1)

    trainer = pl.Trainer(
        max_epochs=25,
        accelerator="auto",
        devices="auto",
        callbacks=[early_stop_callback, checkpoint_callback],
        gradient_clip_val=0.1,
    )

    print("Initiating TFT Training for Ward-level HSI...")
    trainer.fit(model, train_dataloaders=train_loader, val_dataloaders=val_loader)

    best_model_path = checkpoint_callback.best_model_path
    print(f"Training successful. Best weights saved at: {best_model_path}")

    return best_model_path


'''def generate_forecasts(best_model_path: str, val_dataloader):
    """
    Loads the trained model and extracts the actual HSI predictions for the dashboard.
    """
    best_tft = TemporalFusionTransformer.load_from_checkpoint(best_model_path)
    
    # Predict on the validation set
    raw_predictions = best_tft.predict(val_dataloader, mode="raw", return_x=True)
    
    # The output is a tensor containing the 3 quantiles (10%, 50%, 90%)
    # You can route these arrays to your frontend alert generator
    predictions_50th_percentile = raw_predictions.output.prediction[:, :, 1]
    
    return predictions_50th_percentile'''


def generate_and_store_forecasts(best_model_path: str, val_dataloader, output_csv_path: str):
    """
    Loads the trained TFT model, extracts all confidence intervals,
    and flattens the 3D tensor into a database-ready CSV format.
    """
    best_tft = TemporalFusionTransformer.load_from_checkpoint(best_model_path)

    # mode="raw" returns the full 3D tensor: (Wards x Forecast_Horizon x Quantiles)
    raw_predictions = best_tft.predict(val_dataloader, mode="raw", return_x=True)
    predictions_tensor = raw_predictions.output.prediction

    # 1. Convert the tensor to a NumPy array for tabular manipulation
    preds_np = predictions_tensor.detach().cpu().numpy()
    num_wards, forecast_horizon, num_quantiles = preds_np.shape

    # 2. Extract the exact WARD string identifiers from the validation dataset index
    ward_identifiers = val_dataloader.dataset.decoded_index["WARD"].values

    # 3. Flatten the 3D grid into a list of database records
    records = []
    for ward_idx in range(num_wards):
        ward_id = ward_identifiers[ward_idx]

        # Loop through Tomorrow, Day 2, Day 3, etc.
        for day in range(forecast_horizon):
            records.append(
                {
                    "WARD": ward_id,
                    "Forecast_Day_Offset": day + 1,
                    # Extracting all 3 confidence intervals instead of dropping the edges
                    "HSI_Best_Case_10th": preds_np[ward_idx, day, 0],
                    "HSI_Expected_50th": preds_np[ward_idx, day, 1],
                    "HSI_Worst_Case_90th": preds_np[ward_idx, day, 2],
                }
            )

    # 4. Export to a flat CSV for the frontend/dashboard to query
    forecast_df = pd.DataFrame(records).round(2)
    forecast_df.to_csv(output_csv_path, index=False)

    print(f"Success. {len(forecast_df)} forecast records saved to: {output_csv_path}")
    return forecast_df


def execute_pipeline(csv_path: str):
    dataset, train_loader, val_loader = build_tft_dataloaders(csv_path)

    model = initialize_heat_forecaster(dataset)

    early_stop_callback = EarlyStopping(monitor="val_loss", min_delta=1e-4, patience=5, mode="min")

    # 1. Add the ModelCheckpoint to monitor validation loss
    checkpoint_callback = ModelCheckpoint(monitor="val_loss", mode="min", save_top_k=1)

    # 2. Add checkpoint_callback to the callbacks list
    trainer = pl.Trainer(
        max_epochs=25,
        accelerator="auto",
        devices="auto",
        callbacks=[early_stop_callback, checkpoint_callback],
        gradient_clip_val=0.1,
    )

    trainer.fit(model, train_dataloaders=train_loader, val_dataloaders=val_loader)

    # 3. Extract the path directly from your explicit callback variable
    best_model_path = checkpoint_callback.best_model_path

    # Pass the destination path for the final CSV
    final_output_path = ".kolkata_ward_hsi_predictions.csv"
    forecast_df = generate_and_store_forecasts(best_model_path, val_loader, final_output_path)

    return forecast_df


if __name__ == "__main__":
    DATASET_PATH = "./data/kolkata_tft_training_ready.csv"
    best_weights = execute_tft_training(DATASET_PATH)
    forecasts = execute_pipeline("./data/kolkata_tft_training_ready.csv")
    print(forecasts)
