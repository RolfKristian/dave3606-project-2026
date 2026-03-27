class MockDB:
    def __init__(self, expected_queries):
        self.expected_queries = {
            (self.normalize(sql), params): result 
            for (sql, params), result in expected_queries.items()
        }
        self.received = []

    #Eliminates whitespace
    def normalize(self,sql):
        return " ".join(sql.split())
    
    def execute_and_fetch_all(self, query, params=None):
        normalized_query = self.normalize(query)
        key = (normalized_query, params)
        self.received.append(key)

        if key not in self.expected_queries:
            raise AssertionError(f"Unexpected query: {key}")

        return self.expected_queries[key]

    def close(self):
        pass
