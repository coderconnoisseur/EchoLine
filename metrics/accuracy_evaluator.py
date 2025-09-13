import re
import json
import numpy as np
from collections import Counter, defaultdict
from typing import List, Tuple, Dict, Any
import difflib
from dataclasses import dataclass

@dataclass
class TranscriptionMetrics:
    """Container for transcription evaluation metrics"""
    # Word-level metrics
    word_error_rate: float = 0.0
    word_accuracy: float = 0.0
    word_precision: float = 0.0
    word_recall: float = 0.0
    word_f1_score: float = 0.0
    
    # Character-level metrics  
    char_error_rate: float = 0.0
    char_accuracy: float = 0.0
    
    # Sentence-level metrics
    sentence_accuracy: float = 0.0
    
    # Detailed counts
    total_words: int = 0
    correct_words: int = 0
    substitutions: int = 0
    insertions: int = 0
    deletions: int = 0
    
    # Confusion matrix data
    confusion_matrix: Dict[str, Dict[str, int]] = None
    most_confused_words: List[Tuple[str, str, int]] = None

class TranscriptionEvaluator:
    """Evaluates transcription accuracy and generates detailed metrics"""
    
    def __init__(self):
        self.confusion_matrix = defaultdict(lambda: defaultdict(int))
        self.word_operations = []  # Track all operations for detailed analysis
    
    def normalize_text(self, text: str) -> List[str]:
        """Normalize text for fair comparison"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and extra whitespace
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Split into words
        words = text.strip().split()
        
        return words
    
    def calculate_word_error_rate(self, reference: List[str], hypothesis: List[str]) -> Tuple[float, Dict]:
        """
        Calculate Word Error Rate using dynamic programming (Levenshtein distance)
        Returns WER and detailed operation counts
        """
        # Initialize DP table
        r_len, h_len = len(reference), len(hypothesis)
        dp = np.zeros((r_len + 1, h_len + 1), dtype=int)
        
        # Initialize base cases
        for i in range(r_len + 1):
            dp[i][0] = i  # All deletions
        for j in range(h_len + 1):
            dp[0][j] = j  # All insertions
        
        # Fill DP table
        for i in range(1, r_len + 1):
            for j in range(1, h_len + 1):
                if reference[i-1] == hypothesis[j-1]:
                    dp[i][j] = dp[i-1][j-1]  # Match
                else:
                    dp[i][j] = 1 + min(
                        dp[i-1][j],    # Deletion
                        dp[i][j-1],    # Insertion  
                        dp[i-1][j-1]   # Substitution
                    )
        
        # Backtrack to get operations
        operations = self._backtrack_operations(dp, reference, hypothesis)
        
        # Count operation types
        substitutions = sum(1 for op in operations if op[0] == 'substitute')
        insertions = sum(1 for op in operations if op[0] == 'insert')
        deletions = sum(1 for op in operations if op[0] == 'delete')
        
        # Calculate WER
        total_operations = substitutions + insertions + deletions
        wer = total_operations / max(1, len(reference))
        
        return wer, {
            'substitutions': substitutions,
            'insertions': insertions, 
            'deletions': deletions,
            'total_operations': total_operations,
            'operations': operations
        }
    
    def _backtrack_operations(self, dp: np.ndarray, reference: List[str], hypothesis: List[str]) -> List[Tuple]:
        """Backtrack through DP table to get actual operations"""
        operations = []
        i, j = len(reference), len(hypothesis)
        
        while i > 0 or j > 0:
            if i > 0 and j > 0 and reference[i-1] == hypothesis[j-1]:
                # Match - no operation needed
                operations.append(('match', reference[i-1], hypothesis[j-1]))
                i -= 1
                j -= 1
            elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
                # Substitution
                operations.append(('substitute', reference[i-1], hypothesis[j-1]))
                self.confusion_matrix[reference[i-1]][hypothesis[j-1]] += 1
                i -= 1
                j -= 1
            elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
                # Deletion
                operations.append(('delete', reference[i-1], None))
                self.confusion_matrix[reference[i-1]]['<deleted>'] += 1
                i -= 1
            elif j > 0 and dp[i][j] == dp[i][j-1] + 1:
                # Insertion
                operations.append(('insert', None, hypothesis[j-1]))
                self.confusion_matrix['<inserted>'][hypothesis[j-1]] += 1
                j -= 1
        
        return list(reversed(operations))
    
    def calculate_character_error_rate(self, reference: str, hypothesis: str) -> float:
        """Calculate Character Error Rate"""
        ref_chars = list(reference.replace(' ', ''))
        hyp_chars = list(hypothesis.replace(' ', ''))
        
        # Use difflib for character-level comparison
        operations = list(difflib.ndiff(ref_chars, hyp_chars))
        
        errors = sum(1 for op in operations if op.startswith('- ') or op.startswith('+ '))
        cer = errors / max(1, len(ref_chars))
        
        return cer
    
    def evaluate_transcription(self, reference_text: str, hypothesis_text: str) -> TranscriptionMetrics:
        """
        Main evaluation function - calculates all metrics
        """
        # Normalize texts
        ref_words = self.normalize_text(reference_text)
        hyp_words = self.normalize_text(hypothesis_text)
        
        # Calculate word-level metrics
        wer, word_ops = self.calculate_word_error_rate(ref_words, hyp_words)
        
        # Store operations for confusion matrix analyzer
        self.last_operations = word_ops['operations']
        
        # Calculate character-level metrics
        cer = self.calculate_character_error_rate(reference_text, hypothesis_text)
        
        # Word-level accuracy metrics
        correct_words = sum(1 for op in word_ops['operations'] if op[0] == 'match')
        total_words = len(ref_words)
        
        word_accuracy = correct_words / max(1, total_words)
        
        # Precision and Recall calculations
        # Precision = correct words / total hypothesis words
        # Recall = correct words / total reference words
        hyp_word_count = len(hyp_words)
        word_precision = correct_words / max(1, hyp_word_count)
        word_recall = correct_words / max(1, total_words)
        
        # F1 Score
        word_f1 = 2 * (word_precision * word_recall) / max(1, word_precision + word_recall)
        
        # Character accuracy
        char_accuracy = 1.0 - cer
        
        # Sentence accuracy (exact match)
        sentence_accuracy = 1.0 if reference_text.strip().lower() == hypothesis_text.strip().lower() else 0.0
        
        # Get most confused words
        most_confused = self._get_most_confused_words()
        
        return TranscriptionMetrics(
            word_error_rate=wer,
            word_accuracy=word_accuracy,
            word_precision=word_precision,
            word_recall=word_recall,
            word_f1_score=word_f1,
            char_error_rate=cer,
            char_accuracy=char_accuracy,
            sentence_accuracy=sentence_accuracy,
            total_words=total_words,
            correct_words=correct_words,
            substitutions=word_ops['substitutions'],
            insertions=word_ops['insertions'],
            deletions=word_ops['deletions'],
            confusion_matrix=dict(self.confusion_matrix),
            most_confused_words=most_confused
        )
    
    def _get_most_confused_words(self, top_k: int = 10) -> List[Tuple[str, str, int]]:
        """Get the most frequently confused word pairs"""
        confused_pairs = []
        
        for ref_word, substitutions in self.confusion_matrix.items():
            for hyp_word, count in substitutions.items():
                if ref_word != hyp_word and count > 0:
                    confused_pairs.append((ref_word, hyp_word, count))
        
        # Sort by frequency and return top k
        confused_pairs.sort(key=lambda x: x[2], reverse=True)
        return confused_pairs[:top_k]
    
    def evaluate_multiple_samples(self, samples: List[Tuple[str, str]]) -> TranscriptionMetrics:
        """
        Evaluate multiple reference-hypothesis pairs and return aggregate metrics
        """
        all_metrics = []
        
        for reference, hypothesis in samples:
            metrics = self.evaluate_transcription(reference, hypothesis)
            all_metrics.append(metrics)
        
        # Calculate aggregate metrics
        total_words = sum(m.total_words for m in all_metrics)
        total_correct = sum(m.correct_words for m in all_metrics)
        total_substitutions = sum(m.substitutions for m in all_metrics)
        total_insertions = sum(m.insertions for m in all_metrics)
        total_deletions = sum(m.deletions for m in all_metrics)
        
        # Aggregate WER
        total_operations = total_substitutions + total_insertions + total_deletions
        aggregate_wer = total_operations / max(1, total_words)
        
        # Aggregate other metrics
        aggregate_word_accuracy = total_correct / max(1, total_words)
        
        # Average character metrics
        avg_cer = np.mean([m.char_error_rate for m in all_metrics])
        avg_char_accuracy = np.mean([m.char_accuracy for m in all_metrics])
        
        # Average sentence accuracy
        avg_sentence_accuracy = np.mean([m.sentence_accuracy for m in all_metrics])
        
        # Most confused words across all samples
        most_confused = self._get_most_confused_words()
        
        return TranscriptionMetrics(
            word_error_rate=aggregate_wer,
            word_accuracy=aggregate_word_accuracy,
            word_precision=np.mean([m.word_precision for m in all_metrics]),
            word_recall=np.mean([m.word_recall for m in all_metrics]),
            word_f1_score=np.mean([m.word_f1_score for m in all_metrics]),
            char_error_rate=avg_cer,
            char_accuracy=avg_char_accuracy,
            sentence_accuracy=avg_sentence_accuracy,
            total_words=total_words,
            correct_words=total_correct,
            substitutions=total_substitutions,
            insertions=total_insertions,
            deletions=total_deletions,
            confusion_matrix=dict(self.confusion_matrix),
            most_confused_words=most_confused
        )

def print_detailed_metrics(metrics: TranscriptionMetrics, title: str = "Transcription Evaluation Results"):
    """Print detailed metrics in a readable format"""
    print("\n" + "="*60)
    print(f"    {title}")
    print("="*60)
    
    print("\nWORD-LEVEL METRICS:")
    print(f"  Word Error Rate (WER):     {metrics.word_error_rate:.3f} ({metrics.word_error_rate*100:.1f}%)")
    print(f"  Word Accuracy:             {metrics.word_accuracy:.3f} ({metrics.word_accuracy*100:.1f}%)")
    print(f"  Word Precision:            {metrics.word_precision:.3f} ({metrics.word_precision*100:.1f}%)")
    print(f"  Word Recall:               {metrics.word_recall:.3f} ({metrics.word_recall*100:.1f}%)")
    print(f"  Word F1-Score:             {metrics.word_f1_score:.3f} ({metrics.word_f1_score*100:.1f}%)")
    
    print("\nCHARACTER-LEVEL METRICS:")
    print(f"  Character Error Rate (CER): {metrics.char_error_rate:.3f} ({metrics.char_error_rate*100:.1f}%)")
    print(f"  Character Accuracy:        {metrics.char_accuracy:.3f} ({metrics.char_accuracy*100:.1f}%)")
    
    print("\nSENTENCE-LEVEL METRICS:")
    print(f"  Sentence Accuracy:         {metrics.sentence_accuracy:.3f} ({metrics.sentence_accuracy*100:.1f}%)")
    
    print("\nDETAILED COUNTS:")
    print(f"  Total Words:               {metrics.total_words}")
    print(f"  Correct Words:             {metrics.correct_words}")
    print(f"  Substitutions:             {metrics.substitutions}")
    print(f"  Insertions:                {metrics.insertions}")
    print(f"  Deletions:                 {metrics.deletions}")
    
    if metrics.most_confused_words:
        print("\nMOST CONFUSED WORDS:")
        for i, (ref, hyp, count) in enumerate(metrics.most_confused_words[:5], 1):
            print(f"  {i}. '{ref}' → '{hyp}' ({count} times)")
    
    print("="*60)