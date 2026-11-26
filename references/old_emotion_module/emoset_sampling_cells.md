# Renad's EmoSet sampling cells (read-only reference)

Copied verbatim from `team_modules/emotion_keras1.ipynb` in the original project: cells 2, 3, 4, 5 and 7, the ones that define, download and count the EmoSet sample. The notebook ran in Google Colab (paths under `/content`). Hugging Face warnings, progress bars and display objects are left out of the outputs; nothing else is changed.

## Cell 2 (code)

```python
# 8 emotions in EmoSet
CLASSES = ['amusement', 'awe', 'contentment', 'excitement', 'anger', 'disgust', 'fear', 'sadness']
ARABIC  = {'amusement': 'المرح', 'awe': 'الرهبة', 'contentment': 'السكينة', 'excitement': 'الحماس',
           'anger': 'الغضب', 'disgust': 'الاشمئزاز', 'fear': 'الخوف', 'sadness': 'الحزن'}

DATA_DIR = '/content/emoset'          # emoset/train/<emotion>/*.jpg , emoset/val/... , emoset/test/...
OUT      = '/content/emotion_keras'   # model, results and charts
os.makedirs(f'{OUT}/results', exist_ok=True)

IMG_SIZE   = (224, 224)
BATCH_SIZE = 32

# Images per emotion (lower these if you're short on time)
TRAIN_PER_CLASS = 600
VAL_PER_CLASS   = 150
TEST_PER_CLASS  = 400
```

## Cell 3 (markdown)

```markdown
## 1) Data
EmoSet-118K: every image is labelled with one of 8 emotions. I use a balanced sample from each official split (sizes set in the settings cell: 600 / 150 / 400 per emotion).

The next cell downloads the sample from Hugging Face. It takes a while, and at the end it saves `emoset.zip` to your computer. If the session ever disconnects, drag that zip into the Files panel on the left and run the cell again: it will unzip it instead of downloading.
```

## Cell 4 (code)

```python
# Get the data: use emoset.zip if it's in /content, otherwise download from Hugging Face
if not os.path.exists(f'{DATA_DIR}/test') and os.path.exists('/content/emoset.zip'):
    os.system('cd /content && unzip -q -o emoset.zip')
    print('Unzipped emoset.zip')

if not os.path.exists(f'{DATA_DIR}/test'):
    os.system('pip install -q datasets')
    from datasets import load_dataset, Image as HFImage
    from PIL import Image

    def download_emoset(split, per_class):
        ds = load_dataset('Woleek/EmoSet-118K', split=split, streaming=True)
        ds = ds.cast_column('image', HFImage(decode=False))       # don't decode images we skip
        ds = ds.shuffle(seed=42, buffer_size=2000)
        counts = {c: 0 for c in CLASSES}
        for n, row in enumerate(ds, 1):
            emotion = row['emotion']
            if counts[emotion] < per_class:
                img = Image.open(io.BytesIO(row['image']['bytes']))
                img.draft('RGB', (512, 512))                          # fast decode of big JPEGs
                img = img.convert('RGB')
                img.thumbnail((256, 256))
                folder = f'{DATA_DIR}/{split}/{emotion}'
                os.makedirs(folder, exist_ok=True)
                img.save(f'{folder}/{row["image_id"]}.jpg', quality=90)
                counts[emotion] += 1
            if n % 1000 == 0:
                print(split, n, 'rows read, smallest class so far:', min(counts.values()))
            if all(v >= per_class for v in counts.values()):
                break
        print(split, 'done:', counts)

    download_emoset('train', TRAIN_PER_CLASS)
    download_emoset('val', VAL_PER_CLASS)
    download_emoset('test', TEST_PER_CLASS)

    # Backup: download emoset.zip so a disconnect doesn't cost the download again
    from google.colab import files
    os.system('cd /content && zip -qr emoset.zip emoset')
    files.download('/content/emoset.zip')
else:
    print('Data already in', DATA_DIR)
```

Printed output:

```text
train 1000 rows read, smallest class so far: 74
train 2000 rows read, smallest class so far: 155
train 3000 rows read, smallest class so far: 248
train 4000 rows read, smallest class so far: 342
train 5000 rows read, smallest class so far: 434
train 6000 rows read, smallest class so far: 534
train done: {'amusement': 600, 'awe': 600, 'contentment': 600, 'excitement': 600, 'anger': 600, 'disgust': 600, 'fear': 600, 'sadness': 600}
val 1000 rows read, smallest class so far: 87
val done: {'amusement': 150, 'awe': 150, 'contentment': 150, 'excitement': 150, 'anger': 150, 'disgust': 150, 'fear': 150, 'sadness': 150}
test 1000 rows read, smallest class so far: 94
test 2000 rows read, smallest class so far: 181
test 3000 rows read, smallest class so far: 267
test 4000 rows read, smallest class so far: 360
test done: {'amusement': 400, 'awe': 400, 'contentment': 400, 'excitement': 400, 'anger': 400, 'disgust': 400, 'fear': 400, 'sadness': 400}
```

## Cell 5 (code)

```python
train_ds = tf.keras.utils.image_dataset_from_directory(
    f'{DATA_DIR}/train', class_names=CLASSES, image_size=IMG_SIZE,
    batch_size=BATCH_SIZE, shuffle=True, seed=42)

val_ds = tf.keras.utils.image_dataset_from_directory(
    f'{DATA_DIR}/val', class_names=CLASSES, image_size=IMG_SIZE,
    batch_size=BATCH_SIZE, shuffle=False)

test_ds = tf.keras.utils.image_dataset_from_directory(
    f'{DATA_DIR}/test', class_names=CLASSES, image_size=IMG_SIZE,
    batch_size=BATCH_SIZE, shuffle=False)   # test set: only used at the end

test_files = test_ds.file_paths
```

Printed output:

```text
Found 4800 files belonging to 8 classes.
Found 1200 files belonging to 8 classes.
Found 3200 files belonging to 8 classes.
```

## Cell 7 (code)

```python
# How many images per emotion
for name, folder in [('train', 'train'), ('val', 'val'), ('test', 'test')]:
    counts = {c: len(os.listdir(f'{DATA_DIR}/{folder}/{c}')) for c in CLASSES}
    print(name, counts)
```

Printed output:

```text
train {'amusement': 600, 'awe': 600, 'contentment': 600, 'excitement': 600, 'anger': 600, 'disgust': 600, 'fear': 600, 'sadness': 600}
val {'amusement': 150, 'awe': 150, 'contentment': 150, 'excitement': 150, 'anger': 150, 'disgust': 150, 'fear': 150, 'sadness': 150}
test {'amusement': 400, 'awe': 400, 'contentment': 400, 'excitement': 400, 'anger': 400, 'disgust': 400, 'fear': 400, 'sadness': 400}
```
