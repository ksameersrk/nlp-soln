from stat_parser import Parser, display_tree
import sys, os
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'word2vec'))
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Recurrent_NN'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'new'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'unit4', 'MaxEnt'))
import mx
import vanilla_test
import word2vec_run
# import gru_test
import nltk

def get_sentiment(phrase):
    #return str(rnn.get_sentiment(phrase))
    #return mx.get_ans(phrase)
    
    vectors = word2vec_run.get_vectors(phrase)
    if vectors:
        # return vectors
        # return gru_test.sentiment(vectors, os.path.join(os.path.dirname(__file__), '..', 'Recurrent_NN', 'models', 'g5_lines.pkl'))
        # return vanilla_test.sentiment(vectors, os.path.join(os.path.dirname(__file__), '..', 'Recurrent_NN', 'models', 'v5_phrases.pkl'))
        fp = '/home/ksameersrk/Documents/nlp-soln/final/new/rnn_model5.pkl'
        return str(vanilla_test.sentiment(vectors, fp))
    else:
        return "Word Vector is not available"
    

def printTree(node):
    print "ROOT:\n\tLabel :", node.label(), "\n\tText :", ' '.join(node.leaves()), "\n\tSentiment :", get_sentiment(' '.join(node.leaves()))
    getNodes(node)
    print '\n\n'

def getNodes(parent):
    for node in parent:
        if type(node) is nltk.Tree:
            print "Nodes:\n\tLabel :", node.label(), "\n\tText :", ' '.join(node.leaves()), "\n\tSentiment :", get_sentiment(' '.join(node.leaves()))
            getNodes(node)

parser = Parser()
# tree = parser.parse("How can the net amount of entropy of the universe be massively decreased?")


# display_tree(tree)
# tree.draw()

# printTree(tree)
# tree.pretty_print()

while True:
    text = raw_input("Enter the sentence : ")
    tree = parser.parse(text)
    printTree(tree)
    tree.pretty_print()
    print '\n\n'

