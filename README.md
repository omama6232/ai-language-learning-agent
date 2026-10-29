# AI Language Learning Agent

An English grammar tutor built with spaCy and Streamlit. The user types an English sentence and the app finds spelling, subject-verb agreement, article, capitalization, double-negative and plural mistakes, shows the fix, tracks progress, and offers a short quiz when the same mistake is repeated.

## Features
- Rule-based NLP grammar and spelling checker
- Progress page (accuracy over time, mistakes by category)
- Scenario quizzes
- Practice streak calendar
- Login with a separate progress file for every user

## How to run
1. Install the libraries:
   pip install -r requirements.txt
   
   python -m spacy download en_core_web_sm
2. Start the app:
   streamlit run app.py

## Evaluation
The checker was compared with four machine-learning models (Logistic Regression, Linear SVM, Complement Naive Bayes, Random Forest). The rules were kept because no ML model beat them. On a holdout set of 597 sentences: accuracy 85.8%, precision 65.6%, recall 52.2%, F1 58.1%.
Run `python evaluate.py` to repeat the evaluation, and `python train_model.py` for the ML experiment.

## Dataset
JFLEG test set from Kaggle: https://www.kaggle.com/datasets/thedevastator/jfleg-english-grammatical-error-benchmark
