#!/usr/bin/python3

import Const

# to be incremented over time (quick beginning precise later)
EPOCHSTEPS = 100 # number of minibatch samples 
EPOCHSNUM = 1000000 # number of epochs to go for
VALIDATIONSTEPS = 10 # number of minibatch samples to be given for validation (one sample given back for each generator call)
SAMPLENUM = 300 # number of data in a generator sample


from keras.models import Sequential
from keras.models import load_model
from keras.layers import Dense
from keras.layers import Flatten
from keras.layers import Dropout
from keras.callbacks import ModelCheckpoint
from keras.callbacks import CSVLogger
from keras.callbacks import TensorBoard
from keras import backend as K
from keras.utils import plot_model
from time import time
from time import sleep
import matplotlib.pyplot as plt
import numpy as np
import glob, shutil
import pickle
import os
import sys
import subprocess


epdfile=None
currentline=0


def get_chess_training_positions(pickledirectory,validationset=False):
# for multithread see: http://anandology.com/blog/using-iterators-and-generators/
    global currentline
    if not validationset:
        if epdfile==None: 
            if not os.path.exists(Const.ALREADYPROCESSEDDIR): os.mkdir(Const.ALREADYPROCESSEDDIR)
        if currentline==None:
            currentline=0
    while(True):
        sn = 0
        X = [] ; Y = []
        for file in glob.glob(pickledirectory+"/*.pickle"):
            #print("Loading: "+file)
            try:
                (epd, X1, Y1) = pickle.load(open(file, "rb"))
            except:
                print("Error on file: "+str(file))
            else:
                X.append(X1) ; Y.append(Y1)
                sn = sn+1
            if not validationset:
                try:
                    if epdfile!=None:
                        os.remove(file) # created just when needed
                    else:
                        shutil.move(file, Const.ALREADYPROCESSEDDIR)
                except:
                    print("Error moving or removing")
            if sn>=SAMPLENUM: break
        if len(X)>0:
            yield (np.array(X),np.array(Y))
        else:
            print("Not enough elements")
            sleep(160)
        if epdfile!=None and not validationset:
            tcurrentline=currentline; currentline+=EPOCHSTEPS # almost atomic...
            print("./PrepareInput.py "+epdfile+" "+str(currentline)+" "+str(EPOCHSTEPS*SAMPLENUM))
            subprocess.call(['./PrepareInput.py',epdfile,str(tcurrentline),str(EPOCHSTEPS*SAMPLENUM)])


#class LossHistory(keras.callbacks.Callback):
#    def on_train_begin(self, logs={}):
#        self.accs = []
#        self.val_accs = []
#        self.losses = []
#        self.val_losses = []
#    def on_batch_end(self, batch, logs={}):
#        self.accs.append(logs.get('acc'))
#        self.val_accs.append(logs.get('val_acc'))
#        self.losses.append(logs.get('loss'))
#        self.val_losses.append(logs.get('val_loss'))
#        #
#        plt.plot(self.accs)
#        plt.plot(self.val_accs)
#        plt.title('model accuracy')
#        plt.ylabel('accuracy')
#        plt.xlabel('epoch')
#        plt.legend(['train', 'test'], loc='upper left')
#        plt.savefig(Const.MODELFILE+'-log-acc.png')
#        plt.plot(self.losses)
#        plt.plot(self.val_losses)
#        plt.title('model loss')
#        plt.ylabel('loss')
#        plt.xlabel('epoch')
#        plt.legend(['train', 'test'], loc='upper left')
#        plt.savefig(Const.MODELFILE+'-log-loss.png')


#MAIN:

# fix initial seed for reproducibility
seed = 53
np.random.seed(seed)

# create from scratch the model or load it with parameters
if os.path.isfile(Const.MODELFILE+".hdf5"):

    # load it
    model = load_model(Const.MODELFILE+".hdf5")
    print("Loaded model and weights from file")

else:

    #@modelbegin

    modelname = "F30-20180412-MSE-ADAM"

    # create a "simple" sequentially layered model

    model = Sequential()

    model.add(
        Dense(
            64*64,
            input_shape=
                (Const.NUMFEATURES, 8, 8) if K.image_dim_ordering()=="th" \
                     else (8, 8, Const.NUMFEATURES), #tf
            kernel_initializer='random_uniform', # 'zeros', 'uniform', 'random_uniform',
            bias_initializer='zeros',
            activation='linear'))
            # 'hard_sigmoid', 'linear', 'relu', 'sigmoid', 'softplus', 'softsign', 'tanh'

    model.add(Dropout(0.10))

    model.add(
        Flatten())

    model.add(
        Dense(
            64*16,
            kernel_initializer='random_uniform',
            bias_initializer='zeros',
            activation='relu'))

    model.add(
        Dense(
            1,
            kernel_initializer='random_uniform',
            bias_initializer='zeros',
            activation='linear')) # most probably this will be linear in all the models

    # add loss function and optimizer
    model.compile(
        loss='mean_squared_error', # accuracy, mean_squared_logarithmic_error, mean_squared_error
        optimizer='adam',
        metrics=['accuracy']) # just add some metric display to the loss one

    #@modelend

    plot_model(model, to_file=Const.MODELFILE+'.png', show_shapes=True, show_layer_names=True)
    pickle.dump(({"name": modelname}), open(Const.MODELFILE + ".pickle", "wb")) # model attributes
    subprocess.call(["./extract-model.sh"]) # write model to txt file for document purposes
    print("Newly created model with empty weights")


if len(sys.argv)>=2: epdfile=sys.argv[1] 
if len(sys.argv)>=3: currentline=int(sys.argv[2])

# TRAIN! 
model.fit_generator(
    get_chess_training_positions(Const.TOBEPROCESSEDDIR), 
    steps_per_epoch=EPOCHSTEPS, 
    epochs=EPOCHSNUM, 
    verbose=1, 
    callbacks=[
        ModelCheckpoint(Const.MODELFILE+".hdf5", monitor='acc', verbose=1, save_best_only=False, mode='max'),
        CSVLogger(Const.MODELFILE+".log", separator=";", append=True),
        TensorBoard(log_dir="__logs/{}".format(time())),
        #LossHistory(),
        ],
    validation_data=get_chess_training_positions(Const.VALIDATIONDATADIR, True),
    validation_steps=VALIDATIONSTEPS,
    class_weight=None,
    max_queue_size=1000,
    workers=1,
    use_multiprocessing=False,
    initial_epoch=0 )
