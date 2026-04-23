"""
Kesari AI — Model Training Script
A simple training loop for the custom Kesari Transformer model using a character-level tokenizer.
"""
import torch
import json
import os
import argparse
from kesari.ai_brain.model.kesari_net import KesariModel

def get_device():
    if torch.cuda.is_available():
        return 'cuda'
    elif torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'

def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    return text

def train(args):
    # Hyperparameters
    batch_size = args.batch_size
    block_size = args.block_size
    max_iters = args.max_iters
    eval_interval = 100
    learning_rate = args.lr
    eval_iters = 20
    n_embd = args.n_embd
    n_head = args.n_head
    n_layer = args.n_layer
    dropout = args.dropout

    device = get_device()
    print(f"Using device: {device}")

    # Load dataset
    if not os.path.exists(args.data_path):
        print(f"Error: Dataset not found at {args.data_path}")
        print("Please create a text file with conversational data.")
        return

    text = load_data(args.data_path)
    
    # Simple Character-level Tokenizer
    chars = sorted(list(set(text)))
    vocab_size = len(chars)
    print(f"Dataset has {len(text)} characters, vocab size {vocab_size}")
    
    stoi = {ch: i for i, ch in enumerate(chars)}
    itos = {i: ch for i, ch in enumerate(chars)}
    encode = lambda s: [stoi[c] for c in s]
    decode = lambda l: ''.join([itos[i] for i in l])
    
    # Save vocabulary for inference
    output_dir = os.path.dirname(args.output_model)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    vocab_path = args.output_model.replace('.pt', '_vocab.json')
    with open(vocab_path, 'w') as f:
        json.dump({'stoi': stoi, 'itos': itos}, f)
        
    data = torch.tensor(encode(text), dtype=torch.long)
    n = int(0.9 * len(data))
    train_data = data[:n]
    val_data = data[n:]

    def get_batch(split):
        data_split = train_data if split == 'train' else val_data
        ix = torch.randint(len(data_split) - block_size, (batch_size,))
        x = torch.stack([data_split[i:i+block_size] for i in ix])
        y = torch.stack([data_split[i+1:i+block_size+1] for i in ix])
        x, y = x.to(device), y.to(device)
        return x, y

    # Initialize Model
    model = KesariModel(
        vocab_size=vocab_size,
        n_embd=n_embd,
        n_head=n_head,
        n_layer=n_layer,
        block_size=block_size,
        dropout=dropout
    )
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

    @torch.no_grad()
    def estimate_loss():
        out = {}
        model.eval()
        for split in ['train', 'val']:
            losses = torch.zeros(eval_iters)
            for k in range(eval_iters):
                X, Y = get_batch(split)
                logits, loss = model(X, Y)
                losses[k] = loss.item()
            out[split] = losses.mean().item()
        model.train()
        return out

    print("Starting training...")
    best_val_loss = float('inf')
    for iter in range(max_iters):
        # Cosine learning rate decay
        lr_decay = 0.1 + 0.9 * (1 - iter / max_iters)
        for param_group in optimizer.param_groups:
            param_group['lr'] = learning_rate * lr_decay

        if iter % eval_interval == 0 or iter == max_iters - 1:
            losses = estimate_loss()
            flag = " *" if losses['val'] < best_val_loss else ""
            print(f"step {iter}: train loss {losses['train']:.4f}, val loss {losses['val']:.4f}{flag}")
            if losses['val'] < best_val_loss:
                best_val_loss = losses['val']
                # Save best checkpoint
                best_path = args.output_model.replace('.pt', '_best.pt')
                torch.save({
                    'model_state_dict': model.state_dict(),
                    'hyperparameters': {
                        'vocab_size': vocab_size,
                        'n_embd': n_embd,
                        'n_head': n_head,
                        'n_layer': n_layer,
                        'block_size': block_size,
                        'dropout': dropout
                    }
                }, best_path)

        xb, yb = get_batch('train')
        logits, loss = model(xb, yb)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

    # Save Model
    print(f"Training finished. Saving model to {args.output_model}...")
    torch.save({
        'model_state_dict': model.state_dict(),
        'hyperparameters': {
            'vocab_size': vocab_size,
            'n_embd': n_embd,
            'n_head': n_head,
            'n_layer': n_layer,
            'block_size': block_size,
            'dropout': dropout
        }
    }, args.output_model)
    print("Saved!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Train Custom Kesari Model")
    parser.add_argument('--data_path', type=str, default='kesari/dataset.txt', help='Path to training text file')
    parser.add_argument('--output_model', type=str, default='kesari_weights.pt', help='Where to save weights')
    parser.add_argument('--batch_size', type=int, default=32)
    parser.add_argument('--block_size', type=int, default=256)
    parser.add_argument('--max_iters', type=int, default=10000)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--n_embd', type=int, default=256)
    parser.add_argument('--n_head', type=int, default=8)
    parser.add_argument('--n_layer', type=int, default=6)
    parser.add_argument('--dropout', type=float, default=0.1)

    args = parser.parse_args()
    train(args)
