import urllib.robotparser
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter


rp = urllib.robotparser.RobotFileParser()
rp.set_url("https://www.imdb.com/robots.txt")  # No need for BASE_URL here
rp.read()

def can_fetch(url):
    return rp.can_fetch("*", url)

def extract_keywords(text, num_keywords=10):
    """Extracts keywords from a text using NLTK."""
    tokens = word_tokenize(text.lower())  # Tokenize and lowercase
    tokens = [t for t in tokens if t.isalnum()]  # Remove punctuation
    tokens = [t for t in tokens if t not in stopwords.words('english')]  # Remove stopwords
    keyword_counts = Counter(tokens)  # Count word frequencies
    return [keyword for keyword, count in keyword_counts.most_common(num_keywords)]