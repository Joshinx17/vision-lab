from backend.config import ROOT, settings

DATASET_PATH = str(ROOT / 'data' / 'asl_dataset')
MODEL_PATH = str(settings()['model'])
HISTORY_PLOT_PATH = str(ROOT / 'data' / 'training_history.png')
IMG_SIZE = 64
BATCH_SIZE = 32
EPOCHS = 20
NUM_CLASSES = 26
LETTERS = [chr(i) for i in range(65, 91)]
