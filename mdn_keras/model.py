import os
import time
import numpy as np

from keras.models import Sequential
from keras.layers import Input, Dense
from keras.optimizers import Adam
from keras.callbacks import Callback

from tensorflow_probability.python.layers import DistributionLambda
from tensorflow_probability.python.distributions import Mixture, Categorical, MultivariateNormalTriL
from tensorflow_probability.python.bijectors import FillScaleTriL

# -----------------------------------------------------------------------------

def create_model(input_dim, output_dim, learning_rate=1e-4):
    model = Sequential()

    # number of parameters for each component of the mixture model
    loc_size = output_dim
    scale_size = output_dim * (output_dim + 1) // 2
    params_size = loc_size + scale_size

    # number of components for the mixture model
    K = 62
    units = K + K * params_size

    # neural network
    model.add(Input(shape=(input_dim,)))
    model.add(Dense(32, activation='tanh'))
    model.add(Dense(64, activation='tanh'))
    model.add(Dense(128, activation='tanh'))
    model.add(Dense(256, activation='tanh'))
    model.add(Dense(512, activation='tanh'))
    model.add(Dense(1024, activation='tanh'))
    model.add(Dense(2048, activation='tanh'))
    model.add(Dense(units))

    # mixture model
    model.add(DistributionLambda(lambda t: Mixture(
        # parameterized categorical for component selection
        cat=Categorical(logits=t[...,:K]),
        # parameterized components
        components=[MultivariateNormalTriL(
            # parameterized mean of each component
            loc=t[...,K+i*params_size:K+i*params_size+loc_size],
            # parameterized covariance of each component
            scale_tril=FillScaleTriL().forward(
                t[...,K+i*params_size+loc_size:K+i*params_size+loc_size+scale_size]))
                    for i in range(K)])))

    # print model
    model.summary()

    # learning rate, optimizer and loss function
    print('learning_rate:', learning_rate)
    opt = Adam(learning_rate)
    loss = lambda y, rv: -rv.log_prob(y)
    model.compile(optimizer=opt, loss=loss)

    return model

# -----------------------------------------------------------------------------

def save_weights(model):
    fname = 'model_weights.h5'
    print('Writing:', fname)
    model.save_weights(fname)    

def load_weights(model):
    fname = 'model_weights.h5'
    if os.path.isfile(fname):
        print('Reading:', fname)
        model.load_weights(fname)

# -----------------------------------------------------------------------------

class callback(Callback):

    def on_train_begin(self, logs=None):
        self.min_val_loss = np.inf
        self.min_val_weights = self.model.get_weights()
        print('%-10s %10s %12s %12s' % ('time', 'epoch', 'loss', 'val_loss'))

    def on_epoch_end(self, epoch, logs=None):
        t = time.strftime('%H:%M:%S')
        loss = logs['loss']
        val_loss = logs['val_loss']

        if val_loss < self.min_val_loss:
            self.min_val_loss = val_loss
            self.min_val_weights = self.model.get_weights()
            print('%-10s %10d %12.6f %12.6f *' % (t, epoch, loss, val_loss))
        else:
            print('%-10s %10d %12.6f %12.6f' % (t, epoch, loss, val_loss))

        if np.isnan(loss) or np.isnan(val_loss):
            self.model.stop_training = True