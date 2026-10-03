"""
VisionGuard — Train the clip-based fight model (fight_action_best.pt)

Fine-tunes an S3D video network (pre-trained on Kinetics-400) to classify
~2-second clips as fight / non-fight. The result is loaded automatically by
ai/action_recognizer.py when placed at prototype/models/fight_action_best.pt.

Dataset layout (RWF-2000 uses exactly this; any folder of clips works):
    DATA/
      train/Fight/*.avi|mp4     train/NonFight/*.avi|mp4
      val/Fight/*.avi|mp4       val/NonFight/*.avi|mp4

Run on Google Colab (Runtime -> T4 GPU):
    !pip install -q torch torchvision opencv-python-headless kagglehub
    import kagglehub; root = kagglehub.dataset_download("vulamnguyen/rwf2000")
    !python train_fight_action.py --data "$root" --epochs 15
    # then download fight_action_best.pt into prototype/models/

Add your own CCTV clips (e.g. false alarms from your cameras into NonFight)
to the same folders to adapt the model to your scenes.
"""
import argparse
import glob
import os
import random

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision.models.video import S3D_Weights, s3d

CLIP_FRAMES = 16
CLIP_SECONDS = 2.0
SIZE = 224
MEAN = np.array([0.43216, 0.394666, 0.37645], dtype=np.float32)
STD = np.array([0.22803, 0.22145, 0.216989], dtype=np.float32)
EXTS = ("*.avi", "*.mp4", "*.mkv", "*.mov")


def find_split(root, split):
    """Locate <split>/Fight and <split>/NonFight anywhere under root."""
    for d in glob.glob(os.path.join(root, "**", split), recursive=True):
        if os.path.isdir(os.path.join(d, "Fight")) and os.path.isdir(os.path.join(d, "NonFight")):
            return d
    raise FileNotFoundError(f"Could not find {split}/Fight and {split}/NonFight under {root}")


def list_videos(split_dir):
    items = []
    for label, name in ((1, "Fight"), (0, "NonFight")):
        for ext in EXTS:
            items += [(p, label) for p in glob.glob(os.path.join(split_dir, name, ext))]
    return items


def read_clip(path, train):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    if not frames:
        return np.zeros((CLIP_FRAMES, SIZE, SIZE, 3), np.float32)
    span = int(CLIP_SECONDS * fps)
    start = random.randint(0, max(0, len(frames) - span)) if train else max(0, (len(frames) - span) // 2)
    idx = np.linspace(start, min(len(frames) - 1, start + span), CLIP_FRAMES).astype(int)
    clip = [frames[i] for i in idx]

    # Same square crop for all frames (random in training, centre in validation)
    h, w = clip[0].shape[:2]
    side = min(h, w)
    if train:
        side = int(side * random.uniform(0.75, 1.0))
        x0, y0 = random.randint(0, w - side), random.randint(0, h - side)
    else:
        x0, y0 = (w - side) // 2, (h - side) // 2
    flip = train and random.random() < 0.5
    out = []
    for f in clip:
        f = cv2.resize(f[y0:y0 + side, x0:x0 + side], (SIZE, SIZE), interpolation=cv2.INTER_AREA)
        if flip:
            f = f[:, ::-1]
        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    x = np.stack(out).astype(np.float32) / 255.0
    if train:  # brightness/contrast jitter (CCTV lighting varies a lot)
        x = np.clip(x * random.uniform(0.75, 1.25) + random.uniform(-0.08, 0.08), 0, 1)
    return (x - MEAN) / STD


class ClipDataset(Dataset):
    def __init__(self, items, train):
        self.items, self.train = items, train

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        path, label = self.items[i]
        x = torch.from_numpy(read_clip(path, self.train)).permute(3, 0, 1, 2)  # C,T,H,W
        return x, label


def build_model():
    model = s3d(weights=S3D_Weights.KINETICS400_V1)
    model.classifier[1] = nn.Conv3d(1024, 2, kernel_size=1, stride=1, bias=True)
    return model


def evaluate(model, loader, device):
    model.eval()
    tp = fp = tn = fn = 0
    with torch.no_grad(), torch.autocast(device_type=device, enabled=device == "cuda"):
        for x, y in loader:
            pred = model(x.to(device)).argmax(-1).cpu()
            tp += int(((pred == 1) & (y == 1)).sum()); fp += int(((pred == 1) & (y == 0)).sum())
            tn += int(((pred == 0) & (y == 0)).sum()); fn += int(((pred == 0) & (y == 1)).sum())
    acc = (tp + tn) / max(1, tp + tn + fp + fn)
    recall = tp / max(1, tp + fn)        # fights caught
    fpr = fp / max(1, fp + tn)           # false alarms on normal clips
    return acc, recall, fpr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--out", default="fight_action_best.pt")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    train_items = list_videos(find_split(args.data, "train"))
    val_items = list_videos(find_split(args.data, "val"))
    print(f"train clips: {len(train_items)}  val clips: {len(val_items)}  device: {device}")

    tl = DataLoader(ClipDataset(train_items, True), batch_size=args.batch, shuffle=True,
                    num_workers=2, drop_last=True)
    vl = DataLoader(ClipDataset(val_items, False), batch_size=args.batch, num_workers=2)

    model = build_model().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda")
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)

    best = -1.0
    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        for step, (x, y) in enumerate(tl):
            x, y = x.to(device), y.to(device)
            with torch.autocast(device_type=device, enabled=device == "cuda"):
                loss = loss_fn(model(x), y)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            total += loss.item()
        sched.step()
        acc, recall, fpr = evaluate(model, vl, device)
        print(f"epoch {epoch + 1}/{args.epochs}  loss {total / max(1, len(tl)):.3f}  "
              f"val acc {acc:.1%}  fights caught {recall:.1%}  false alarms {fpr:.1%}")
        score = acc - 0.5 * fpr
        if score > best:
            best = score
            torch.save({"model": model.state_dict(), "val_acc": acc, "recall": recall, "fpr": fpr}, args.out)
            print(f"  saved {args.out}")
    print("done — copy", args.out, "to prototype/models/")


if __name__ == "__main__":
    main()
