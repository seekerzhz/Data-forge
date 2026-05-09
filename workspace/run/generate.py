import random
import os

def generate_small_easy():
    cases = []
    # Case 1: n=2, q=4 (full grid)
    cases.append((2, [(1,1), (1,2), (2,1), (2,2)]))
    # Case 2: n=3, q=5 (basic queries)
    cases.append((3, [(2,2), (3,3), (2,3), (3,1), (3,2)]))
    # Case 3: n=2, q=1 (single cell)
    cases.append((2, [(1,1)]))
    # Case 4: n=4, q=3 (sparse)
    cases.append((4, [(1,4), (3,2), (4,3)]))
    # Case 5: n=5, q=6 (some diagonals)
    cases.append((5, [(1,1), (2,2), (3,3), (4,4), (5,5), (1,5)]))
    return cases

def generate_special_edge():
    cases = []
    # Case 6: All cells in first row
    n = 1000
    q = n
    queries = [(1, c) for c in range(1, n+1)]
    cases.append((n, queries))
    
    # Case 7: All cells in first column
    n = 1500
    q = n
    queries = [(r, 1) for r in range(1, n+1)]
    cases.append((n, queries))
    
    # Case 8: Single test case with n=2000, q=2000 (diagonal)
    n = 2000
    q = 2000
    queries = [(i, i) for i in range(1, q+1)]
    cases.append((n, queries))
    
    # Case 9: Two test cases, n=1000 each, q=1000 each (sparse)
    n1, n2 = 1000, 1000
    q1, q2 = 1000, 1000
    queries1 = [(random.randint(1, n1), random.randint(1, n1)) for _ in range(q1)]
    queries1 = list(dict.fromkeys(queries1))  # Remove duplicates
    queries2 = [(random.randint(1, n2), random.randint(1, n2)) for _ in range(q2)]
    queries2 = list(dict.fromkeys(queries2))
    cases.append((n1, queries1))
    cases.append((n2, queries2))
    
    # Case 10: n=10000, q=1 (only one cell)
    cases.append((10000, [(5000, 5000)]))
    return cases

def generate_medium_random(num_cases=20):
    cases = []
    random.seed(42)
    total_n = 0
    total_q = 0
    for _ in range(num_cases):
        n = random.randint(100, 1000)
        q = random.randint(n, min(n*n, 10000))
        total_n += n
        total_q += q
        # Generate unique queries
        queries = set()
        while len(queries) < q:
            r = random.randint(1, n)
            c = random.randint(1, n)
            queries.add((r, c))
        cases.append((n, list(queries)))
    return cases

def generate_stress_tests(num_cases=20):
    cases = []
    random.seed(123)
    total_n = 0
    total_q = 0
    for i in range(num_cases):
        # Generate large n but sum to <=2e6
        if i < 10:
            n = 200000
            q = min(n*n, 200000)
        else:
            n = 100000
            q = min(n*n, 150000)
        # Ensure total constraints met
        if total_n + n > 2e6:
            n = int(2e6 - total_n)
        if n < 2:
            n = 2
        q = min(q, int(2e6 - total_q), n*n)
        if q < 1:
            q = 1
            
        # Generate unique queries
        queries = set()
        while len(queries) < q:
            r = random.randint(1, n)
            c = random.randint(1, n)
            queries.add((r, c))
        cases.append((n, list(queries)))
        
        total_n += n
        total_q += q
    return cases

def write_cases_to_file(cases, filename):
    with open(filename, 'w') as f:
        f.write(f"{len(cases)}\n")
        for n, queries in cases:
            f.write(f"{n} {len(queries)}\n")
            for r, c in queries:
                f.write(f"{r} {c}\n")

def main():
    random.seed(0)
    for i in range(1, 51):
        if 1 <= i <= 5:
            cases = [generate_small_easy()[i-1]]
        elif 6 <= i <= 10:
            cases = [generate_special_edge()[i-6]]
        elif 11 <= i <= 30:
            cases = generate_medium_random(num_cases=1)
        else:
            cases = generate_stress_tests(num_cases=1)
        filename = f"{i}.in"
        write_cases_to_file(cases, filename)

if __name__ == "__main__":
    main()
