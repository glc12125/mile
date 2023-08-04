MILE_PATH=$HOME/dev/mile
mkdir -p $MILE_PATH/data/trainval/train
mkdir -p $MILE_PATH/data/trainval/val
mv $MILE_PATH/data/trainval/Town01 $MILE_PATH/data/trainval/train/
echo "Moving training data from Town01/0050-0099 to Town03/"
mkdir -p $MILE_PATH/data/trainval/train/Town03/
sudo mv $MILE_PATH/data/trainval/train/Town01/005* $MILE_PATH/data/trainval/train/Town03/
sudo mv $MILE_PATH/data/trainval/train/Town01/006* $MILE_PATH/data/trainval/train/Town03/
sudo mv $MILE_PATH/data/trainval/train/Town01/007* $MILE_PATH/data/trainval/train/Town03/
sudo mv $MILE_PATH/data/trainval/train/Town01/008* $MILE_PATH/data/trainval/train/Town03/
sudo mv $MILE_PATH/data/trainval/train/Town01/009* $MILE_PATH/data/trainval/train/Town03/
echo "Moving training data from Town01/0100-0149 to Town04/"
mkdir -p $MILE_PATH/data/trainval/train/Town04/
sudo mv $MILE_PATH/data/trainval/train/Town01/010* $MILE_PATH/data/trainval/train/Town04/
sudo mv $MILE_PATH/data/trainval/train/Town01/011* $MILE_PATH/data/trainval/train/Town04/
sudo mv $MILE_PATH/data/trainval/train/Town01/012* $MILE_PATH/data/trainval/train/Town04/
sudo mv $MILE_PATH/data/trainval/train/Town01/013* $MILE_PATH/data/trainval/train/Town04/
sudo mv $MILE_PATH/data/trainval/train/Town01/014* $MILE_PATH/data/trainval/train/Town04/
echo "Moving training data from Town01/0150-0199 to Town06/"
mkdir -p $MILE_PATH/data/trainval/train/Town06/
sudo mv $MILE_PATH/data/trainval/train/Town01/015* $MILE_PATH/data/trainval/train/Town06/
sudo mv $MILE_PATH/data/trainval/train/Town01/016* $MILE_PATH/data/trainval/train/Town06/
sudo mv $MILE_PATH/data/trainval/train/Town01/017* $MILE_PATH/data/trainval/train/Town06/
sudo mv $MILE_PATH/data/trainval/train/Town01/018* $MILE_PATH/data/trainval/train/Town06/
sudo mv $MILE_PATH/data/trainval/train/Town01/019* $MILE_PATH/data/trainval/train/Town06/

echo "Preparign valuation data"
mv $MILE_PATH/data/trainval/Town02 $MILE_PATH/data/trainval/val/
echo "Moving valuation data from Town02/0050-0099 to Town05/"
mkdir -p $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/005* $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/006* $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/007* $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/008* $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/009* $MILE_PATH/data/trainval/val/Town05/