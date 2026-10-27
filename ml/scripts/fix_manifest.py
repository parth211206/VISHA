import pandas as pd
import os
import hashlib

manifest_path = r"data\manifests\image_manifest_v1.csv"
leakage_safe_path = r"data\manifests\image_manifest_v1_leakage_safe.csv"
backup_path = r"data\manifests\image_manifest_v1.csv.bak"

# Load manifest
df = pd.read_csv(manifest_path)

# Helper to normalize path to absolute
def norm_path(p):
    if os.path.isabs(p):
        return os.path.normpath(p)
    else:
        return os.path.normpath(os.path.join(os.getcwd(), p))

# Precompute normalized paths and verify existence/readability
missing = []
unreadable = []
hash_to_rows = {}  # hash -> list of (idx, norm_path, split, label)
for idx, row in df.iterrows():
    p = norm_path(row['absolute_path'])
    if not os.path.isfile(p):
        missing.append((idx, p))
        continue
    try:
        with open(p, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        unreadable.append((idx, p, e))
        continue
    hash_to_rows.setdefault(file_hash, []).append((idx, p, row['split'], row['binary_label']))

if missing:
    print("ERROR: Missing files referenced by manifest:")
    for idx, p in missing[:5]:
        print(f"  Row {idx}: {p}")
    exit(1)
if unreadable:
    print("ERROR: Unreadable files:")
    for idx, p, e in unreadable[:5]:
        print(f"  Row {idx}: {p} - {e}")
    exit(1)

print(f"Successfully processed {len(df)} manifest rows, {len(hash_to_rows)} unique image contents.")

# Determine which row indices to disable for training and evaluation (set use_in_training=False, use_in_evaluation=False)
to_disable = set()  # indices of rows where we will set flags to False (only if currently True)

for h, entries in hash_to_rows.items():
    # Separate by split
    train_entries = [e for e in entries if e[2] == 'train']
    test_entries = [e for e in entries if e[2] == 'test']
    # Case 1: hash appears in both train and test -> disable all train entries
    if train_entries and test_entries:
        for idx, p, split, label in train_entries:
            to_disable.add(idx)
    # Case 2: hash appears only in train, with duplicates -> keep one active if possible, disable the rest
    elif train_entries and not test_entries:
        if len(train_entries) > 1:
            # Find an active training entry (use_in_training == True) if any
            active_candidates = [e for e in train_entries if df.at[e[0], 'use_in_training']]
            if active_candidates:
                # Keep the first active entry (by original index)
                keep_idx = min(active_candidates, key=lambda x: x[0])[0]
            else:
                # No active entry; keep the first entry by index (we will not activate it)
                keep_idx = train_entries[0][0]
            for idx, p, split, label in train_entries:
                if idx != keep_idx:
                    to_disable.add(idx)
    # Case 3: hash appears only in test -> do nothing (preserve all test entries)
    # Case 4: hash appears only in train with a single entry -> do nothing

# Ensure we do not reactivate any previously disabled entry: we will only set False, never True.
# We'll create a copy of the dataframe to modify.
df_corrected = df.copy()

# Ensure the flag columns exist (they should)
if 'use_in_training' not in df_corrected.columns:
    df_corrected['use_in_training'] = True
if 'use_in_evaluation' not in df_corrected.columns:
    df_corrected['use_in_evaluation'] = True

# Apply disabling: set to False only if currently True (to avoid toggling)
changed_count = 0
for idx in to_disable:
    if df_corrected.at[idx, 'use_in_training']:
        df_corrected.at[idx, 'use_in_training'] = False
        changed_count += 1
    if df_corrected.at[idx, 'use_in_evaluation']:
        df_corrected.at[idx, 'use_in_evaluation'] = False
        changed_count += 1

print(f"Number of flag changes (use_in_training or use_in_evaluation set to False): {changed_count}")

# Verify that active training and test image contents are disjoint
def get_active_hashes(df, use_train_flag, use_eval_flag, split_val):
    """Return set of SHA-256 hashes for rows where the flag is True and split matches."""
    hashes = set()
    for idx, row in df.iterrows():
        if row['split'] == split_val:
            flag_ok = row[use_train_flag] if use_train_flag else row[use_eval_flag]
            if flag_ok:
                p = norm_path(row['absolute_path'])
                if os.path.isfile(p):
                    with open(p, 'rb') as f:
                        hashes.add(hashlib.sha256(f.read()).hexdigest())
                else:
                    # Should not happen as we checked earlier
                    pass
    return hashes

active_train_hashes = get_active_hashes(df_corrected, 'use_in_training', 'use_in_evaluation', 'train')
active_test_hashes = get_active_hashes(df_corrected, 'use_in_evaluation', 'use_in_training', 'test')  # note: flag is use_in_evaluation
overlap = active_train_hashes & active_test_hashes
print(f"Active training image count: {len(active_train_hashes)}")
print(f"Active test image count: {len(active_test_hashes)}")
print(f"Number of image hashes appearing in both active training and test: {len(overlap)}")
if overlap:
    print("ERROR: Leakage detected after correction!")
    exit(1)
else:
    print("SUCCESS: No exact-content overlap between active training and test sets.")

# Verify that unrelated columns and values are unchanged
cols_to_compare = [col for col in df.columns if col not in ['use_in_training', 'use_in_evaluation']]
if not df[cols_to_compare].equals(df_corrected[cols_to_compare]):
    print("ERROR: Unrelated columns were modified!")
    exit(1)
else:
    print("SUCCESS: All unrelated columns and values are unchanged.")

# Verify row count unchanged
if len(df) != len(df_corrected):
    print("ERROR: Row count changed!")
    exit(1)
else:
    print(f"Row count unchanged: {len(df)}")

# Verify that test rows' flags are unchanged
test_rows = df[df['split'] == 'test']
test_rows_corrected = df_corrected[df_corrected['split'] == 'test']
if not test_rows[['use_in_training', 'use_in_evaluation']].equals(test_rows_corrected[['use_in_training', 'use_in_evaluation']]):
    print("ERROR: Test rows' flags were modified!")
    exit(1)
else:
    print("SUCCESS: All test rows' flags remain unchanged.")

# Verify that no previously disabled entry has been reactivated
# For each flag, ensure that any row where original flag was False remains False in corrected
for flag in ['use_in_training', 'use_in_evaluation']:
    orig_false = df[flag] == False
    corr_false = df_corrected[flag] == False
    # Check that orig_false implies corr_false (i.e., orig_false & ~corr_false is all False)
    if (orig_false & ~corr_false).any():
        print(f"ERROR: Previously disabled {flag} entries were reactivated!")
        exit(1)
print("SUCCESS: No previously disabled entry has been reactivated.")

# Write the leakage-safe manifest
df_corrected.to_csv(leakage_safe_path, index=False)
print(f"Leakage-safe manifest written to: {leakage_safe_path}")

# Report before and after counts
# Original active counts (based on original flags)
df_orig = pd.read_csv(manifest_path)  # reload original to get original flags
orig_train_active = df_orig[(df_orig['use_in_training'] == True) & (df_orig['split'] == 'train')]
orig_test_active = df_orig[(df_orig['use_in_evaluation'] == True) & (df_orig['split'] == 'test')]
print(f"Original active training entries: {len(orig_train_active)}")
print(f"Original active test entries: {len(orig_test_active)}")

# New active counts
new_train_active = df_corrected[(df_corrected['use_in_training'] == True) & (df_corrected['split'] == 'train')]
new_test_active = df_corrected[(df_corrected['use_in_evaluation'] == True) & (df_corrected['split'] == 'test')]
print(f"New active training entries: {len(new_train_active)}")
print(f"New active test entries: {len(new_test_active)}")

# Also compute unique image contents in active sets to double-check
def get_active_unique_hashes(df):
    train_hashes = set()
    test_hashes = set()
    for idx, row in df.iterrows():
        p = norm_path(row['absolute_path'])
        if not os.path.isfile(p):
            continue
        with open(p, 'rb') as f:
            h = hashlib.sha256(f.read()).hexdigest()
        if row['use_in_training'] == True and row['split'] == 'train':
            train_hashes.add(h)
        if row['use_in_evaluation'] == True and row['split'] == 'test':
            test_hashes.add(h)
    return train_hashes, test_hashes

orig_train_h, orig_test_h = get_active_unique_hashes(df_orig)
new_train_h, new_test_h = get_active_unique_hashes(df_corrected)
print(f"Original unique image contents in active training: {len(orig_train_h)}")
print(f"Original unique image contents in active test: {len(orig_test_h)}")
print(f"Original overlap: {len(orig_train_h & orig_test_h)}")
print(f"New unique image contents in active training: {len(new_train_h)}")
print(f"New unique image contents in active test: {len(new_test_h)}")
print(f"New overlap: {len(new_train_h & new_test_h)} (should be 0)")

print("Manifest correction completed successfully.")