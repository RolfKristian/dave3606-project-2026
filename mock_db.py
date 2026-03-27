class MockDB:
    def __init__(self, expected_queries):
        self.expected_queries = expected_queries
        self.received = []

    def execute_and_fetch_all(self, query, params=None):
        key = (query, params)
        self.received.append(key)

        if key not in self.expected_queries:
            raise AssertionError(f"Unexpected query: {key}")

        return self.expected_queries[key]

    def close(self):
        pass
