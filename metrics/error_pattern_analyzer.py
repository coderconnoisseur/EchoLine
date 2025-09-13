import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict, Counter
import re
from typing import Dict, List, Tuple, Any
import statistics

class ConfusionMatrixAnalyzer:
    """Analyzes confusion matrices and error patterns in transcription"""
    
    def __init__(self):
        self.confusion_data = defaultdict(lambda: defaultdict(int))
        self.word_accuracy_data = defaultdict(lambda: {'correct': 0, 'total': 0})
        self.total_operations = []
        
    def add_confusion_data(self, confusion_matrix: Dict[str, Dict[str, int]]):
        """Add confusion matrix data for analysis"""
        for ref_word, substitutions in confusion_matrix.items():
            for hyp_word, count in substitutions.items():
                self.confusion_data[ref_word][hyp_word] += count
                
                # Track word accuracy properly
                if ref_word == hyp_word:
                    # This is a correct match
                    self.word_accuracy_data[ref_word]['correct'] += count
                    self.word_accuracy_data[ref_word]['total'] += count
                else:
                    # This is an error
                    self.word_accuracy_data[ref_word]['total'] += count
                    # Also count the hypothesis word if it's not an insertion
                    if hyp_word != '<inserted>' and ref_word != '<deleted>':
                        if hyp_word not in self.word_accuracy_data:
                            self.word_accuracy_data[hyp_word]['correct'] = 0
                            self.word_accuracy_data[hyp_word]['total'] = 0
    
    def add_operation_list(self, operations: List[Tuple[str, str, str]]):
        """Add operation list from alignment for better accuracy tracking"""
        self.total_operations.extend(operations)
        
        # Track accuracy from operations
        for operation, ref_word, hyp_word in operations:
            if operation == 'match':
                # Correct match
                self.word_accuracy_data[ref_word]['correct'] += 1
                self.word_accuracy_data[ref_word]['total'] += 1
            elif operation in ['substitute', 'delete']:
                # Error with reference word
                if ref_word:
                    self.word_accuracy_data[ref_word]['total'] += 1
            elif operation == 'insert':
                # Insertion - affects hypothesis word
                if hyp_word:
                    # Count as error for the inserted word
                    self.word_accuracy_data[hyp_word]['total'] += 1
    
    def calculate_word_accuracies(self) -> Dict[str, float]:
        """Calculate individual word accuracies"""
        accuracies = {}
        
        for word, stats in self.word_accuracy_data.items():
            if stats['total'] > 0:
                accuracies[word] = stats['correct'] / stats['total']
            else:
                accuracies[word] = 0.0
                
        return accuracies
    
    def get_most_confused_pairs(self, top_k: int = 10) -> List[Tuple[str, str, int]]:
        """Get the most frequently confused word pairs"""
        confused_pairs = []
        
        for ref_word, substitutions in self.confusion_data.items():
            for hyp_word, count in substitutions.items():
                if ref_word != hyp_word and count > 0:  # Only actual errors
                    confused_pairs.append((ref_word, hyp_word, count))
        
        # Sort by frequency
        confused_pairs.sort(key=lambda x: x[2], reverse=True)
        return confused_pairs[:top_k]
    
    def analyze_error_patterns(self) -> Dict[str, int]:
        """Analyze different types of errors"""
        patterns = {
            'phonetic_errors': 0,
            'length_errors': 0,
            'capitalization_errors': 0,
            'punctuation_errors': 0,
            'semantic_errors': 0
        }
        
        for ref_word, substitutions in self.confusion_data.items():
            for hyp_word, count in substitutions.items():
                if ref_word != hyp_word and ref_word not in ['<inserted>', '<deleted>'] and hyp_word not in ['<inserted>', '<deleted>']:
                    # Analyze the type of error
                    if ref_word.lower() == hyp_word.lower():
                        patterns['capitalization_errors'] += count
                    elif self._is_phonetically_similar(ref_word, hyp_word):
                        patterns['phonetic_errors'] += count
                    elif abs(len(ref_word) - len(hyp_word)) > 2:
                        patterns['length_errors'] += count
                    elif self._has_punctuation_difference(ref_word, hyp_word):
                        patterns['punctuation_errors'] += count
                    else:
                        patterns['semantic_errors'] += count
        
        return patterns
    
    def _is_phonetically_similar(self, word1: str, word2: str) -> bool:
        """Check if two words are phonetically similar"""
        # Simple phonetic similarity check
        # This could be enhanced with proper phonetic algorithms
        word1_clean = re.sub(r'[^a-zA-Z]', '', word1.lower())
        word2_clean = re.sub(r'[^a-zA-Z]', '', word2.lower())
        
        if len(word1_clean) == 0 or len(word2_clean) == 0:
            return False
        
        # Check for common phonetic substitutions
        phonetic_pairs = [
            ('ph', 'f'), ('ck', 'k'), ('c', 'k'), ('s', 'z'),
            ('i', 'y'), ('ie', 'y'), ('tion', 'shun')
        ]
        
        for pair in phonetic_pairs:
            word1_sub = word1_clean.replace(pair[0], pair[1])
            word2_sub = word2_clean.replace(pair[0], pair[1])
            if word1_sub == word2_clean or word2_sub == word1_clean:
                return True
        
        # Check edit distance
        edit_dist = self._calculate_edit_distance(word1_clean, word2_clean)
        similarity = 1 - (edit_dist / max(len(word1_clean), len(word2_clean)))
        return similarity > 0.7  # 70% similarity threshold
    
    def _has_punctuation_difference(self, word1: str, word2: str) -> bool:
        """Check if words differ only in punctuation"""
        clean1 = re.sub(r'[^a-zA-Z0-9]', '', word1.lower())
        clean2 = re.sub(r'[^a-zA-Z0-9]', '', word2.lower())
        return clean1 == clean2 and clean1 != ''
    
    def _calculate_edit_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance"""
        if len(s1) < len(s2):
            return self._calculate_edit_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def generate_detailed_report(self) -> str:
        """Generate a comprehensive analysis report"""
        accuracies = self.calculate_word_accuracies()
        confused_pairs = self.get_most_confused_pairs()
        error_patterns = self.analyze_error_patterns()
        
        # Calculate statistics
        accuracy_values = [acc for acc in accuracies.values() if acc > 0]  # Only consider words that appeared
        total_words = len(accuracies)
        unique_words = len([w for w in accuracies.keys() if w not in ['<inserted>', '<deleted>']])
        
        report = []
        report.append("=" * 60)
        report.append("FIXED CONFUSION MATRIX ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")
        
        report.append("OVERALL STATISTICS:")
        report.append(f"  Total word types: {total_words}")
        report.append(f"  Unique content words: {unique_words}")
        report.append(f"  Words with instances: {len(accuracy_values)}")
        report.append("")
        
        report.append("MOST CONFUSED WORD PAIRS:")
        for i, (ref, hyp, count) in enumerate(confused_pairs[:10], 1):
            report.append(f"  {i:2d}. '{ref}' → '{hyp}' ({count} times)")
        report.append("")
        
        report.append("ERROR PATTERN ANALYSIS:")
        for pattern, count in error_patterns.items():
            pattern_name = pattern.replace('_', ' ').title()
            report.append(f"  {pattern_name}: {count}")
        report.append("")
        
        if accuracy_values:
            report.append("WORD ACCURACY DISTRIBUTION:")
            report.append(f"  Mean accuracy: {statistics.mean(accuracy_values):.3f}")
            report.append(f"  Median accuracy: {statistics.median(accuracy_values):.3f}")
            report.append(f"  Min accuracy: {min(accuracy_values):.3f}")
            report.append(f"  Max accuracy: {max(accuracy_values):.3f}")
            report.append("")
            
            # Show best performing words
            best_words = sorted(accuracies.items(), key=lambda x: x[1], reverse=True)
            best_words = [(w, acc) for w, acc in best_words if w not in ['<inserted>', '<deleted>'] and acc > 0]
            
            if best_words:
                report.append("BEST PERFORMING WORDS:")
                for i, (word, acc) in enumerate(best_words[:10], 1):
                    total_count = self.word_accuracy_data[word]['total']
                    report.append(f"  {i:2d}. '{word}' - {acc:.3f} accuracy ({total_count} occurrences)")
                report.append("")
            
            # Show worst performing words (but with reasonable occurrences)
            worst_words = sorted(accuracies.items(), key=lambda x: x[1])
            worst_words = [(w, acc) for w, acc in worst_words if w not in ['<inserted>', '<deleted>'] and self.word_accuracy_data[w]['total'] >= 2]
            
            if worst_words:
                report.append("WORST PERFORMING WORDS (2+ occurrences):")
                for i, (word, acc) in enumerate(worst_words[:10], 1):
                    total_count = self.word_accuracy_data[word]['total']
                    report.append(f"  {i:2d}. '{word}' - {acc:.3f} accuracy ({total_count} occurrences)")
        else:
            report.append("WORD ACCURACY DISTRIBUTION:")
            report.append("  No accuracy data available - check alignment algorithm")
        
        report.append("=" * 60)
        return "\n".join(report)
    
    def generate_visualization(self, output_file: str = "confusion_matrix_heatmap.png"):
        """Generate confusion matrix heatmap"""
        try:
            # Get top confused words for visualization
            confused_pairs = self.get_most_confused_pairs(20)
            
            if not confused_pairs:
                print("No confusion data available for visualization")
                return
            
            # Create matrix for visualization
            words = list(set([pair[0] for pair in confused_pairs] + [pair[1] for pair in confused_pairs]))
            words = [w for w in words if w not in ['<inserted>', '<deleted>']][:15]  # Limit size
            
            if len(words) < 2:
                print("Insufficient data for meaningful visualization")
                return
            
            matrix = np.zeros((len(words), len(words)))
            word_to_idx = {word: i for i, word in enumerate(words)}
            
            for ref_word, hyp_word, count in confused_pairs:
                if ref_word in word_to_idx and hyp_word in word_to_idx:
                    matrix[word_to_idx[ref_word]][word_to_idx[hyp_word]] = count
            
            # Create heatmap
            plt.figure(figsize=(12, 10))
            sns.heatmap(matrix, 
                       xticklabels=words, 
                       yticklabels=words,
                       annot=True, 
                       fmt='g',
                       cmap='Reds',
                       cbar_kws={'label': 'Confusion Count'})
            
            plt.title('Word Confusion Matrix\n(Reference Words → Hypothesis Words)')
            plt.xlabel('Hypothesis Words')
            plt.ylabel('Reference Words')
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"Confusion matrix heatmap saved to: {output_file}")
            
        except Exception as e:
            print(f"Error generating visualization: {e}")
    
    def analyze_phonetic_similarity(self, output_file: str = "phonetic_analysis.png"):
        """Analyze and visualize phonetic similarity patterns"""
        try:
            confused_pairs = self.get_most_confused_pairs(50)
            
            phonetic_similarities = []
            error_types = []
            
            for ref_word, hyp_word, count in confused_pairs:
                if ref_word not in ['<inserted>', '<deleted>'] and hyp_word not in ['<inserted>', '<deleted>']:
                    similarity = self._calculate_phonetic_similarity(ref_word, hyp_word)
                    phonetic_similarities.append(similarity)
                    
                    if self._is_phonetically_similar(ref_word, hyp_word):
                        error_types.append('Phonetic')
                    elif ref_word.lower() == hyp_word.lower():
                        error_types.append('Capitalization')
                    elif abs(len(ref_word) - len(hyp_word)) > 2:
                        error_types.append('Length')
                    else:
                        error_types.append('Other')
            
            if not phonetic_similarities:
                print("No phonetic data available for analysis")
                return
            
            # Create visualization
            plt.figure(figsize=(10, 6))
            
            # Scatter plot of phonetic similarities
            colors = {'Phonetic': 'red', 'Capitalization': 'blue', 'Length': 'green', 'Other': 'orange'}
            for error_type in set(error_types):
                indices = [i for i, et in enumerate(error_types) if et == error_type]
                similarities = [phonetic_similarities[i] for i in indices]
                plt.scatter(similarities, [error_type] * len(similarities), 
                           c=colors.get(error_type, 'gray'), label=error_type, alpha=0.6)
            
            plt.xlabel('Phonetic Similarity Score')
            plt.ylabel('Error Type')
            plt.title('Phonetic Similarity Analysis of Confused Word Pairs')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"Phonetic analysis saved to: {output_file}")
            
        except Exception as e:
            print(f"Error generating phonetic analysis: {e}")
    
    def _calculate_phonetic_similarity(self, word1: str, word2: str) -> float:
        """Calculate phonetic similarity score between two words"""
        if not word1 or not word2:
            return 0.0
        
        word1_clean = re.sub(r'[^a-zA-Z]', '', word1.lower())
        word2_clean = re.sub(r'[^a-zA-Z]', '', word2.lower())
        
        if not word1_clean or not word2_clean:
            return 0.0
        
        edit_dist = self._calculate_edit_distance(word1_clean, word2_clean)
        max_len = max(len(word1_clean), len(word2_clean))
        
        return 1.0 - (edit_dist / max_len)