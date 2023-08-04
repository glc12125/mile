#MILE_PATH=$HOME/dev/mile
MILE_PATH=/home/dev/mile
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

echo "Preparing valuation data"
mv $MILE_PATH/data/trainval/Town02 $MILE_PATH/data/trainval/val/
echo "Moving valuation data from Town02/0050-0099 to Town05/"
mkdir -p $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/005* $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/006* $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/007* $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/008* $MILE_PATH/data/trainval/val/Town05/
sudo mv $MILE_PATH/data/trainval/val/Town02/009* $MILE_PATH/data/trainval/val/Town05/

echo "Preparing mini training data"
echo "Syn linking trainval/train/Town01/0000-0006 to mini/train/Town01/"
mkdir -p $MILE_PATH/data/mini/train/Town01/
ln -s $MILE_PATH/data/trainval/train/Town01/0000 $MILE_PATH/data/mini/train/Town01/0000
ln -s $MILE_PATH/data/trainval/train/Town01/0001 $MILE_PATH/data/mini/train/Town01/0001
ln -s $MILE_PATH/data/trainval/train/Town01/0002 $MILE_PATH/data/mini/train/Town01/0002
ln -s $MILE_PATH/data/trainval/train/Town01/0003 $MILE_PATH/data/mini/train/Town01/0003
ln -s $MILE_PATH/data/trainval/train/Town01/0004 $MILE_PATH/data/mini/train/Town01/0004
ln -s $MILE_PATH/data/trainval/train/Town01/0005 $MILE_PATH/data/mini/train/Town01/0005
ln -s $MILE_PATH/data/trainval/train/Town01/0006 $MILE_PATH/data/mini/train/Town01/0006
echo "Syn linking trainval/train/Town03/0050-0056 to mini/train/Town03/"
mkdir -p $MILE_PATH/data/mini/train/Town03/
ln -s $MILE_PATH/data/trainval/train/Town03/0050 $MILE_PATH/data/mini/train/Town03/0050
ln -s $MILE_PATH/data/trainval/train/Town03/0051 $MILE_PATH/data/mini/train/Town03/0051
ln -s $MILE_PATH/data/trainval/train/Town03/0052 $MILE_PATH/data/mini/train/Town03/0052
ln -s $MILE_PATH/data/trainval/train/Town03/0053 $MILE_PATH/data/mini/train/Town03/0053
ln -s $MILE_PATH/data/trainval/train/Town03/0054 $MILE_PATH/data/mini/train/Town03/0054
ln -s $MILE_PATH/data/trainval/train/Town03/0055 $MILE_PATH/data/mini/train/Town03/0055
ln -s $MILE_PATH/data/trainval/train/Town03/0056 $MILE_PATH/data/mini/train/Town03/0056
echo "Syn linking trainval/train/Town04/0100-0106 to mini/train/Town04/"
mkdir -p $MILE_PATH/data/mini/train/Town04/
ln -s $MILE_PATH/data/trainval/train/Town04/0100 $MILE_PATH/data/mini/train/Town04/0100
ln -s $MILE_PATH/data/trainval/train/Town04/0101 $MILE_PATH/data/mini/train/Town04/0101
ln -s $MILE_PATH/data/trainval/train/Town04/0102 $MILE_PATH/data/mini/train/Town04/0102
ln -s $MILE_PATH/data/trainval/train/Town04/0103 $MILE_PATH/data/mini/train/Town04/0103
ln -s $MILE_PATH/data/trainval/train/Town04/0104 $MILE_PATH/data/mini/train/Town04/0104
ln -s $MILE_PATH/data/trainval/train/Town04/0105 $MILE_PATH/data/mini/train/Town04/0105
ln -s $MILE_PATH/data/trainval/train/Town04/0106 $MILE_PATH/data/mini/train/Town04/0106
echo "Syn linking trainval/train/Town06/0150-0156 to mini/train/Town06/"
mkdir -p $MILE_PATH/data/mini/train/Town06/
ln -s $MILE_PATH/data/trainval/train/Town06/0150 $MILE_PATH/data/mini/train/Town06/0150
ln -s $MILE_PATH/data/trainval/train/Town06/0151 $MILE_PATH/data/mini/train/Town06/0151
ln -s $MILE_PATH/data/trainval/train/Town06/0152 $MILE_PATH/data/mini/train/Town06/0152
ln -s $MILE_PATH/data/trainval/train/Town06/0153 $MILE_PATH/data/mini/train/Town06/0153
ln -s $MILE_PATH/data/trainval/train/Town06/0154 $MILE_PATH/data/mini/train/Town06/0154
ln -s $MILE_PATH/data/trainval/train/Town06/0155 $MILE_PATH/data/mini/train/Town06/0155
ln -s $MILE_PATH/data/trainval/train/Town06/0156 $MILE_PATH/data/mini/train/Town06/0156

echo "Preparing mini val data"
echo "Syn linking trainval/val/Town02/0000-0013 to mini/val/Town02/"
mkdir -p $MILE_PATH/data/mini/val/Town02/
ln -s $MILE_PATH/data/trainval/val/Town02/0000 $MILE_PATH/data/mini/val/Town02/0000
ln -s $MILE_PATH/data/trainval/val/Town02/0001 $MILE_PATH/data/mini/val/Town02/0001
ln -s $MILE_PATH/data/trainval/val/Town02/0002 $MILE_PATH/data/mini/val/Town02/0002
ln -s $MILE_PATH/data/trainval/val/Town02/0003 $MILE_PATH/data/mini/val/Town02/0003
ln -s $MILE_PATH/data/trainval/val/Town02/0004 $MILE_PATH/data/mini/val/Town02/0004
ln -s $MILE_PATH/data/trainval/val/Town02/0005 $MILE_PATH/data/mini/val/Town02/0005
ln -s $MILE_PATH/data/trainval/val/Town02/0006 $MILE_PATH/data/mini/val/Town02/0006
ln -s $MILE_PATH/data/trainval/val/Town02/0007 $MILE_PATH/data/mini/val/Town02/0007
ln -s $MILE_PATH/data/trainval/val/Town02/0008 $MILE_PATH/data/mini/val/Town02/0008
ln -s $MILE_PATH/data/trainval/val/Town02/0009 $MILE_PATH/data/mini/val/Town02/0009
ln -s $MILE_PATH/data/trainval/val/Town02/0010 $MILE_PATH/data/mini/val/Town02/0010
ln -s $MILE_PATH/data/trainval/val/Town02/0011 $MILE_PATH/data/mini/val/Town02/0011
ln -s $MILE_PATH/data/trainval/val/Town02/0012 $MILE_PATH/data/mini/val/Town02/0012
ln -s $MILE_PATH/data/trainval/val/Town02/0013 $MILE_PATH/data/mini/val/Town02/0013
echo "Syn linking trainval/val/Town05/0050-0063 to mini/val/Town05/"
mkdir -p $MILE_PATH/data/mini/val/Town05/
ln -s $MILE_PATH/data/trainval/val/Town05/0050 $MILE_PATH/data/mini/val/Town05/0050
ln -s $MILE_PATH/data/trainval/val/Town05/0051 $MILE_PATH/data/mini/val/Town05/0051
ln -s $MILE_PATH/data/trainval/val/Town05/0052 $MILE_PATH/data/mini/val/Town05/0052
ln -s $MILE_PATH/data/trainval/val/Town05/0053 $MILE_PATH/data/mini/val/Town05/0053
ln -s $MILE_PATH/data/trainval/val/Town05/0054 $MILE_PATH/data/mini/val/Town05/0054
ln -s $MILE_PATH/data/trainval/val/Town05/0055 $MILE_PATH/data/mini/val/Town05/0055
ln -s $MILE_PATH/data/trainval/val/Town05/0056 $MILE_PATH/data/mini/val/Town05/0056
ln -s $MILE_PATH/data/trainval/val/Town05/0057 $MILE_PATH/data/mini/val/Town05/0057
ln -s $MILE_PATH/data/trainval/val/Town05/0058 $MILE_PATH/data/mini/val/Town05/0058
ln -s $MILE_PATH/data/trainval/val/Town05/0059 $MILE_PATH/data/mini/val/Town05/0059
ln -s $MILE_PATH/data/trainval/val/Town05/0060 $MILE_PATH/data/mini/val/Town05/0060
ln -s $MILE_PATH/data/trainval/val/Town05/0061 $MILE_PATH/data/mini/val/Town05/0061
ln -s $MILE_PATH/data/trainval/val/Town05/0062 $MILE_PATH/data/mini/val/Town05/0062
ln -s $MILE_PATH/data/trainval/val/Town05/0063 $MILE_PATH/data/mini/val/Town05/0063