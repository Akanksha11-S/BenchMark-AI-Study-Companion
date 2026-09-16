"""Small curated notes corpus for the DSA chatbot's retrieval step.

This is intentionally simple (keyword/tag overlap, no embeddings) so the
retrieval logic is transparent and easy to explain in an interview. Swapping
this for a vector store (e.g. embeddings + cosine similarity, or a hybrid
BM25 + vector approach) is a natural next step and worth mentioning as a
known limitation / future improvement.
"""

from typing import List, Dict

KB: List[Dict] = [
    {
        "title": "Arrays",
        "tags": ["array", "index", "contiguous"],
        "content": (
            "Arrays store elements in contiguous memory, so indexing is O(1) "
            "but inserting or removing in the middle is O(n) because later "
            "elements must shift."
        ),
        "code": "nums = [4, 2, 7]\nnums.insert(1, 9)  # O(n): shifts 2 and 7 right",
    },
    {
        "title": "Linked Lists",
        "tags": ["linked list", "node", "pointer"],
        "content": (
            "A linked list stores nodes connected by pointers. Insertion or "
            "deletion at a known node is O(1), but reaching that node takes "
            "O(n) since there's no random access."
        ),
        "code": "class Node:\n    def __init__(self, val):\n        self.val = val\n        self.next = None",
    },
    {
        "title": "Stacks and Queues",
        "tags": ["stack", "queue", "lifo", "fifo"],
        "content": (
            "A stack is LIFO (push/pop from one end) and a queue is FIFO "
            "(enqueue at one end, dequeue at the other). Stacks suit undo "
            "history and DFS; queues suit BFS and task scheduling."
        ),
        "code": "stack = []\nstack.append(1); stack.append(2)\nstack.pop()  # returns 2",
    },
    {
        "title": "Binary Search Trees",
        "tags": ["bst", "tree", "search"],
        "content": (
            "A BST keeps every left descendant smaller and every right "
            "descendant larger than a node, giving O(log n) search, insert, "
            "and delete when the tree stays balanced."
        ),
        "code": (
            "def search(root, target):\n"
            "    if not root or root.val == target:\n"
            "        return root\n"
            "    return search(root.left, target) if target < root.val else search(root.right, target)"
        ),
    },
    {
        "title": "Sorting Algorithms",
        "tags": ["sort", "quicksort", "mergesort", "complexity"],
        "content": (
            "Merge sort splits, sorts, and merges in O(n log n) with extra "
            "memory. Quicksort partitions around a pivot, averaging "
            "O(n log n) in place but degrading to O(n^2) on bad pivots."
        ),
        "code": (
            "def merge_sort(a):\n"
            "    if len(a) <= 1:\n"
            "        return a\n"
            "    mid = len(a) // 2\n"
            "    left, right = merge_sort(a[:mid]), merge_sort(a[mid:])\n"
            "    return merge(left, right)"
        ),
    },
    {
        "title": "Graph Traversal",
        "tags": ["graph", "bfs", "dfs"],
        "content": (
            "BFS explores level by level using a queue, finding shortest "
            "paths in unweighted graphs. DFS explores depth-first using a "
            "stack or recursion, suiting cycle detection and topological "
            "order."
        ),
        "code": (
            "def bfs(graph, start):\n"
            "    visited, q = {start}, [start]\n"
            "    while q:\n"
            "        node = q.pop(0)\n"
            "        for nb in graph[node]:\n"
            "            if nb not in visited:\n"
            "                visited.add(nb); q.append(nb)"
        ),
    },
    {
        "title": "Dynamic Programming",
        "tags": ["dp", "memoization", "subproblem"],
        "content": (
            "DP solves a problem by combining solutions to overlapping "
            "subproblems, storing results (memoization) so each subproblem "
            "is computed once instead of exponentially many times."
        ),
        "code": (
            "def fib(n, memo={}):\n"
            "    if n in memo:\n"
            "        return memo[n]\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    memo[n] = fib(n - 1, memo) + fib(n - 2, memo)\n"
            "    return memo[n]"
        ),
    },
    {
        "title": "Hashing",
        "tags": ["hash", "hashmap", "dictionary", "collision"],
        "content": (
            "A hash map maps keys to array slots via a hash function, "
            "giving average O(1) lookup, insert, and delete. Collisions are "
            "handled with chaining or open addressing."
        ),
        "code": (
            "seen = {}\n"
            "for i, n in enumerate(nums):\n"
            "    if target - n in seen:\n"
            "        return [seen[target - n], i]\n"
            "    seen[n] = i"
        ),
    },
]

STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "in", "for", "and", "or",
    "when", "should", "i", "use", "what", "how", "does", "do", "vs",
    "between",
}


def tokenize(text: str) -> List[str]:
    import re

    words = re.split(r"[^a-z0-9]+", text.lower())
    return [w for w in words if w and w not in STOPWORDS]


def retrieve(query: str, top_n: int = 2) -> List[Dict]:
    """Score each KB doc by keyword/tag overlap with the query and return the
    top matches. Returns [] if nothing scores above zero."""
    q_terms = tokenize(query)
    q_lower = query.lower()
    scored = []
    for doc in KB:
        doc_terms = tokenize(doc["title"] + " " + " ".join(doc["tags"]) + " " + doc["content"])
        score = sum(1 for t in q_terms if t in doc_terms)
        score += sum(2 for tag in doc["tags"] if tag in q_lower)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _, doc in scored[:top_n]]


def get_topics() -> List[str]:
    return [doc["title"] for doc in KB]


def get_doc(title: str) -> Dict:
    for doc in KB:
        if doc["title"] == title:
            return doc
    return None
