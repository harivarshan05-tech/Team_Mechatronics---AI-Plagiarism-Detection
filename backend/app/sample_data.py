"""
Realistic sample submissions demonstrating all 6 required plagiarism benchmark scenarios
across Python, C++, and Java.
"""

def get_sample_submissions():
    return [
        # Scenario 1 & 2: Base QuickSort and AI-renamed QuickSort
        {
            "id": "sub_py_01",
            "filename": "quicksort_original.py",
            "student_id": "alice_smith",
            "content": '''"""
QuickSort implementation in Python
Author: Alice
"""

def partition(arr, low, high):
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1

def quicksort(arr, low, high):
    if low < high:
        pi = partition(arr, low, high)
        quicksort(arr, low, pi - 1)
        quicksort(arr, pi + 1, high)

def sort_array(numbers):
    quicksort(numbers, 0, len(numbers) - 1)
    return numbers

if __name__ == "__main__":
    test_data = [64, 34, 25, 12, 22, 11, 90]
    print(sort_array(test_data))
''',
        },
        {
            "id": "sub_py_02",
            "filename": "quicksort_identical_copy.py",
            "student_id": "bob_jones",
            "content": '''"""
QuickSort implementation in Python
Author: Bob
"""

def partition(arr, low, high):
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1

def quicksort(arr, low, high):
    if low < high:
        pi = partition(arr, low, high)
        quicksort(arr, low, pi - 1)
        quicksort(arr, pi + 1, high)

def sort_array(numbers):
    quicksort(numbers, 0, len(numbers) - 1)
    return numbers

if __name__ == "__main__":
    test_data = [64, 34, 25, 12, 22, 11, 90]
    print(sort_array(test_data))
''',
        },
        {
            "id": "sub_py_03",
            "filename": "quicksort_ai_renamed.py",
            "student_id": "charlie_brown",
            "content": '''# AI Refactored sorting utility
# Uses randomized divide-and-conquer strategy

def divide_subsequence(elements, start_idx, end_idx):
    pivot_item = elements[end_idx]
    pointer = start_idx - 1
    for cursor in range(start_idx, end_idx):
        if elements[cursor] <= pivot_item:
            pointer += 1
            elements[pointer], elements[cursor] = elements[cursor], elements[pointer]
    elements[pointer + 1], elements[end_idx] = elements[end_idx], elements[pointer + 1]
    return pointer + 1

def recursive_sorter(collection, left_bound, right_bound):
    if left_bound < right_bound:
        split_point = divide_subsequence(collection, left_bound, right_bound)
        recursive_sorter(collection, left_bound, split_point - 1)
        recursive_sorter(collection, split_point + 1, right_bound)

def execute_sort(items_list):
    recursive_sorter(items_list, 0, len(items_list) - 1)
    return items_list

sample_input = [64, 34, 25, 12, 22, 11, 90]
print(execute_sort(sample_input))
''',
        },

        # Scenario 3: Reordered Functions
        {
            "id": "sub_py_04",
            "filename": "geometry_calc_a.py",
            "student_id": "david_miller",
            "content": '''import math

def calculate_circle_area(radius):
    if radius <= 0:
        return 0.0
    return math.pi * (radius ** 2)

def calculate_cylinder_volume(radius, height):
    base_area = calculate_circle_area(radius)
    return base_area * height

def calculate_sphere_volume(radius):
    if radius <= 0:
        return 0.0
    return (4.0 / 3.0) * math.pi * (radius ** 3)
''',
        },
        {
            "id": "sub_py_05",
            "filename": "geometry_calc_b_reordered.py",
            "student_id": "emma_watson",
            "content": '''import math

# Functions placed in opposite order
def calculate_sphere_volume(r):
    if r <= 0:
        return 0.0
    return (4.0 / 3.0) * math.pi * (r ** 3)

def calculate_cylinder_volume(r, h):
    area = calculate_circle_area(r)
    return area * h

def calculate_circle_area(r):
    if r <= 0:
        return 0.0
    return math.pi * (r ** 2)
''',
        },

        # Scenario 4: Loop converted to Recursion
        {
            "id": "sub_py_06",
            "filename": "factorial_iterative.py",
            "student_id": "frank_castle",
            "content": '''def compute_factorial(n):
    if n < 0:
        return -1
    result = 1
    for i in range(1, n + 1):
        result = result * i
    return result

def run_tests():
    for val in [1, 5, 10]:
        print(compute_factorial(val))

run_tests()
''',
        },
        {
            "id": "sub_py_07",
            "filename": "factorial_recursive.py",
            "student_id": "grace_hopper",
            "content": '''def compute_factorial(n):
    if n < 0:
        return -1
    if n == 0 or n == 1:
        return 1
    return n * compute_factorial(n - 1)

def run_tests():
    for val in [1, 5, 10]:
        print(compute_factorial(val))

run_tests()
''',
        },

        # Scenario 5: Logically similar but differently implemented (Binary Search)
        {
            "id": "sub_py_08",
            "filename": "binary_search_iterative.py",
            "student_id": "harry_potter",
            "content": '''def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
''',
        },
        {
            "id": "sub_py_09",
            "filename": "binary_search_alternative.py",
            "student_id": "isla_fisher",
            "content": '''def find_index(sorted_list, key):
    left = 0
    right = len(sorted_list)
    while left < right:
        center = left + (right - left) // 2
        if sorted_list[center] < key:
            left = center + 1
        else:
            right = center
    if left < len(sorted_list) and sorted_list[left] == key:
        return left
    return -1
''',
        },

        # Scenario 6: Completely Unrelated Solutions
        {
            "id": "sub_py_10",
            "filename": "matrix_multiply.py",
            "student_id": "jack_sparrow",
            "content": '''def matrix_multiply(A, B):
    rows_A = len(A)
    cols_A = len(A[0])
    rows_B = len(B)
    cols_B = len(B[0])
    
    if cols_A != rows_B:
        raise ValueError("Incompatible matrix dimensions")
        
    result = [[0 for _ in range(cols_B)] for _ in range(rows_A)]
    for i in range(rows_A):
        for j in range(cols_B):
            for k in range(cols_A):
                result[i][j] += A[i][k] * B[k][j]
    return result
''',
        },
        {
            "id": "sub_py_11",
            "filename": "web_text_parser.py",
            "student_id": "kevin_bacon",
            "content": '''import re

def extract_hyperlinks_and_tags(html_document):
    link_pattern = re.compile(r'href=["\'](https?://[^"\']+)["\']')
    found_urls = link_pattern.findall(html_document)
    
    tag_cleaner = re.compile(r'<[^>]+>')
    plain_text = tag_cleaner.sub('', html_document)
    
    words = plain_text.lower().split()
    frequency = {}
    for w in words:
        frequency[w] = frequency.get(w, 0) + 1
    return {"links": found_urls, "word_count": len(words), "frequency": frequency}
''',
        },

        # C++ Samples
        {
            "id": "sub_cpp_12",
            "filename": "bfs_graph.cpp",
            "student_id": "lucas_lee",
            "content": '''#include <iostream>
#include <vector>
#include <queue>

using namespace std;

void bfs(int startNode, int numVertices, const vector<vector<int>>& adjList) {
    vector<bool> visited(numVertices, false);
    queue<int> q;

    visited[startNode] = true;
    q.push(startNode);

    while (!q.empty()) {
        int current = q.front();
        q.pop();
        cout << current << " ";

        for (int neighbor : adjList[current]) {
            if (!visited[neighbor]) {
                visited[neighbor] = true;
                q.push(neighbor);
            }
        }
    }
}
''',
        },
        {
            "id": "sub_cpp_13",
            "filename": "bfs_graph_ai_renamed.cpp",
            "student_id": "maya_lin",
            "content": '''#include <iostream>
#include <vector>
#include <queue>

// Rewritten Breadth-First-Search
void traverseBreadthFirst(int rootVertex, int totalNodes, const std::vector<std::vector<int>>& graph) {
    std::vector<bool> seen(totalNodes, false);
    std::queue<int> frontier;

    seen[rootVertex] = true;
    frontier.push(rootVertex);

    while (!frontier.empty()) {
        int activeNode = frontier.front();
        frontier.pop();
        std::cout << activeNode << " ";

        for (int adjacent : graph[activeNode]) {
            if (!seen[adjacent]) {
                seen[adjacent] = true;
                frontier.push(adjacent);
            }
        }
    }
}
''',
        },

        # Java Samples
        {
            "id": "sub_java_14",
            "filename": "BinarySearchTree.java",
            "student_id": "noah_clark",
            "content": '''public class BinarySearchTree {
    static class Node {
        int data;
        Node left, right;
        Node(int val) {
            this.data = val;
            left = right = null;
        }
    }

    private Node root;

    public void insert(int val) {
        root = insertRec(root, val);
    }

    private Node insertRec(Node curr, int val) {
        if (curr == null) {
            return new Node(val);
        }
        if (val < curr.data) {
            curr.left = insertRec(curr.left, val);
        } else if (val > curr.data) {
            curr.right = insertRec(curr.right, val);
        }
        return curr;
    }

    public boolean search(int val) {
        Node curr = root;
        while (curr != null) {
            if (curr.data == val) return true;
            if (val < curr.data) curr = curr.left;
            else curr = curr.right;
        }
        return false;
    }
}
''',
        },
        {
            "id": "sub_java_15",
            "filename": "BST_Refactored.java",
            "student_id": "olivia_wilde",
            "content": '''public class BST_Refactored {
    static class TreeNode {
        int key;
        TreeNode leftChild, rightChild;
        TreeNode(int v) {
            this.key = v;
            leftChild = rightChild = null;
        }
    }

    private TreeNode rootNode;

    public void add(int v) {
        rootNode = addRecursive(rootNode, v);
    }

    private TreeNode addRecursive(TreeNode current, int value) {
        if (current == null) {
            return new TreeNode(value);
        }
        if (value < current.key) {
            current.leftChild = addRecursive(current.leftChild, value);
        } else if (value > current.key) {
            current.rightChild = addRecursive(current.rightChild, value);
        }
        return current;
    }

    public boolean contains(int target) {
        TreeNode ptr = rootNode;
        while (ptr != null) {
            if (ptr.key == target) return true;
            if (target < ptr.key) ptr = ptr.leftChild;
            else ptr = ptr.rightChild;
        }
        return false;
    }
}
''',
        },
    ]
