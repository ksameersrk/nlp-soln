import numpy as np
import scipy.signal
import sklearn
import dill
import pickle
import csv
import sys
import copy

from gensim.models import Word2Vec

model = Word2Vec.load('w2vmodel')

def clip(v):
        x = v[:10]
        if len(x) % 2 == 0:
            b = a = (10 - len(x)) / 2
        else:
            b = (10 - len(x)) / 2
            a = b + 1

        return np.lib.pad(np.array(x), ((b, a), (0, 0) ), 'constant')

def save_model(brnn):
    with open('cnn_model_%s.pkl' % TYPE, 'wb') as f:
        dill.dump(brnn, f)

def load_model():
    with open('cnn_model_%s.pkl' % TYPE, 'rb') as f:
        brnn = dill.load(f)
    return brnn

class CNN:
    def __init__(self, filter_dim, num_filters, stride, output_size, learning_rate=0.01):
        N, h, w = (num_filters, (10 - filter_dim) / stride, (64 - filter_dim) / stride ) # result of convolution
        self.result_shape =  (N, h / 2 + 1, w / 2 + 1) # result of pooling
        self.filter_shape = (num_filters, filter_dim, filter_dim)
        self.input_shape = (10, 64)

        self.learning_rate = learning_rate
        self.f = np.tanh
        self.f_prime = lambda x: 1 - (x ** 2)
        self.stride = stride
        self.Wxh = np.random.randn(*self.filter_shape) * np.sqrt(2.0 / (sum(self.filter_shape)))
        self.Why = np.random.randn(output_size, np.prod(self.result_shape)) * np.sqrt(2.0 / (np.prod(self.filter_shape) + output_size))
        self.bh = np.zeros((h + 1, w + 1))
        self.by = np.zeros((output_size, 1))

        self.mWxh, self.mWhy = np.zeros_like(self.Wxh), np.zeros_like(self.Why)
        self.mbh, self.mby = np.zeros_like(self.bh), np.zeros_like(self.by) # memory variables for Adagrad

    def forward(self, x):
        h = self.f(np.array([scipy.signal.convolve2d(x, w, mode='valid') + self.bh for w in self.Wxh]))

        h_prev = np.copy(h)
        num_filters, height, width = h.shape
        h = np.amax(h.reshape(num_filters, height/2, 2, width/2, 2).swapaxes(2, 3).reshape(num_filters, height/2, width/2, 4), axis=3)

        mask = np.equal(h_prev, h.repeat(2, axis=1).repeat(2, axis=2)).astype(int)

        y = self.f(np.dot(self.Why, h.reshape(-1, 1)) + self.by)
        p = np.exp(y) / np.sum(np.exp(y))

        return h, mask, y, p

    i = 0
    def backprop(self, x, h, mask, y, dy):
        global i
        dWxh, dWhy = np.zeros_like(self.Wxh), np.zeros_like(self.Why)
        dbh, dby = np.zeros_like(self.bh), np.zeros_like(self.by)
        tmp = dy * self.f_prime(y)
        dWhy -= np.multiply(tmp, h.reshape(1, -1))
        dby -= tmp
        dh = np.dot(self.Why.T, dy)
        dhraw = dh * self.f_prime(h.reshape(-1, 1))
        dhraw = dhraw.reshape(self.result_shape).repeat(2, axis=1).repeat(2, axis=2)
        dhraw = np.multiply(dhraw, mask)
        dWxh -= np.array([np.rot90(scipy.signal.convolve2d(x, w, 'valid')) for w in dhraw])
        dbh -= np.mean(dhraw, axis=0)

        for dparam in [dWxh, dWhy, dbh, dby]:
            np.clip(dparam, -5, 5, out=dparam) # clip to mitigate exploding gradients

        return dWxh, dWhy, dbh, dby

    def train(self, training_data, validation_data, epochs=5):
        for e in range(epochs):
            print('epoch #:{}'.format(e + 1))

            for x, y in zip(*training_data):
                h, mask, y, p = self.forward(x)
                t = np.argmax(y)
                dy = p
                dy[t] -= 1
                dWxh, dWhy, dbh, dby = self.backprop(x, h, mask, y, dy)
                self.param_update(dWxh, dWhy, dbh, dby)

            print("(Validation Accuracy: {:.2f}%)".format(self.calculate(validation_data) * 100))

        print("\nComplete.")

    def param_update(self, dWxh, dWhy, dbh, dby):
        # perform parameter update with Adagrad
        for param, dparam, mem in zip([self.Wxh, self.Why, self.bh, self.by],
                                    [dWxh, dWhy, dbh, dby],
                                    [self.mWxh, self.mWhy, self.mbh, self.mby]):
            mem += dparam * dparam
            param -= self.learning_rate * dparam / np.sqrt(mem + 1e-5) # adagrad update

    def calculate(self, testing_data, test=False, client=False, sent=[]):
        correct = 0
        predictions = {x : 0 for x in range(TYPE)}
        outputs = {x : 0 for x in range(TYPE)}

        if client:
            op = np.argmax(self.forward(sent)[-1])
            print 'Predicted - ',op
        else:
            l = 0
            for x, y in zip(*testing_data):
                op = np.argmax(self.forward(x)[-1])
                tr = np.argmax(y)
                predictions[op] += 1
                outputs[tr] += 1
                correct = correct + 1 if op == tr else correct + 0
                l += 1

            if test:
                print 'Outputs are:\t', outputs
                print 'Predictions are:\t', predictions

            return (correct + 0.0) / l


def load_data(filename, count):
    i = 0
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        inputs = []
        outputs = []
        for row in reader:
            inputs.append(row[0])
            outputs.append(int(row[1]))
            i += 1
            if i == count:
                break
        return inputs, outputs

def w2v(sentence):
    words = []
    for word in sentence.split():
        try:
            words.append(model[word])
        except Exception:
            pass

    return np.array(words)

def one_hot(x):
    def three(x):
        if x < 2:
            return 0

        elif x > 2:
            return 2

        else:
            return 1

    v = np.zeros(TYPE)

    if TYPE == 3:
        v[three(x)] = 1
    else:
        v[x] = 1

    return v

def sent_vec(sentence):
    v = w2v(sentence)
    if v.size > 0:
        return clip(v)
    else:
        print 'Word Not In Vocab'
    return v

def parse(t_i,t_t):
    _inputs = list()
    _targets = list()
    for i in range(len(t_i)):
        v = w2v(t_i[i])
        if len(v) == 0:
            continue

        _inputs.append(clip(v))
        _targets.append(one_hot(t_t[i]))
    return [_inputs,_targets]

if __name__ == "__main__":
    DATA_SIZE = 10000
    TYPE = 5

    FILTER_DIM = 3
    NUM_FILTERS = 5
    STRIDE = 1
    POOL_DIM = 2
    OUTPUT_SIZE = TYPE

    train_size = DATA_SIZE * 0.8
    val_size = DATA_SIZE * 0.1
    test_size = DATA_SIZE * 0.1

    t_i, t_t =  load_data('train.csv', train_size)
    v_i, v_t = load_data('dev.csv', val_size)
    ts_i, ts_t =  load_data('test.csv', test_size)

    training_inputs, training_targets = parse(t_i,t_t)

    validation_inputs, validation_targets = parse(v_i,v_t)

    testing_inputs, testing_targets = parse(ts_i,ts_t)

    EPOCHS = 5
    LEARNING_RATE = 0.1

    TRAIN = False
    TEST = False
    CLIENT = True


    CNN = None
    if TRAIN:
        CNN = CNN(FILTER_DIM, NUM_FILTERS, STRIDE, TYPE, LEARNING_RATE)
        CNN.train(training_data=(training_inputs, training_targets), validation_data=(validation_inputs, validation_targets), epochs=EPOCHS)
        save_model(CNN)
    elif CLIENT:
        CNN = load_model()
        print 'MODEL LOADED-'
        while True:
            sentence = raw_input('Enter Sentence : ')
            vector = sent_vec(sentence)
            if vector.size == 0:
                break
            else:
                op = CNN.calculate((testing_inputs, testing_targets), False, True, vector)
    else:
        CNN = load_model()
        accuracy = CNN.calculate((testing_inputs, testing_targets), True)
        print("Accuracy: {:.2f}%".format(accuracy * 100))