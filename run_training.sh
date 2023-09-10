CUDA_VISIBLE_DEVICES=0,1 PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32 python train.py --config /home/dev/mile/mile/configs/mile_3080x2.yml DATASET.DATAROOT /home/dev/mile/data
#CUDA_VISIBLE_DEVICES=0,1 PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32 python train.py --config /home/dev/mile/mile/configs/debug.yml DATASET.DATAROOT /home/dev/mile/data
