from neo4j import GraphDatabase
from typing import Optional, Dict, Any

class GraphDB:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="12345678"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_node(self, label: str, properties: Dict[str, Any], key: str = "id"):
        """
        Tạo node nếu chưa tồn tại (theo field key).
        """
        with self.driver.session() as session:
            props = {k: v for k, v in properties.items() if v is not None}
            query = f"MERGE (n:{label} {{{key}: ${key}}}) SET n += $props RETURN n"
            session.run(query, **properties, props=props)

    def get_node(self, label: str, key: str, value: str) -> Optional[Dict[str, Any]]:
        with self.driver.session() as session:
            query = f"MATCH (n:{label} {{{key}: $value}}) RETURN n"
            result = session.run(query, value=value).single()
            return dict(result["n"]) if result else None

    def update_node(self, label: str, key: str, value: str, new_props: Dict[str, Any]):
        with self.driver.session() as session:
            query = f"MATCH (n:{label} {{{key}: $value}}) SET n += $props RETURN n"
            result = session.run(query, value=value, props=new_props).single()
            return dict(result["n"]) if result else None

    def delete_node(self, label: str, key: str, value: str):
        with self.driver.session() as session:
            query = f"MATCH (n:{label} {{{key}: $value}}) DETACH DELETE n RETURN COUNT(*) as deleted"
            result = session.run(query, value=value).single()
            return result["deleted"] if result else 0

    def list_nodes(self, label: str):
        with self.driver.session() as session:
            query = f"MATCH (n:{label}) RETURN n"
            result = session.run(query)
            return [dict(r["n"]) for r in result]

  
    def create_relationship(self, start_label: str, start_key: str, start_val: str,
                            rel_type: str, end_label: str, end_key: str, end_val: str,
                            props: Optional[Dict[str, Any]] = None):
        """
        Tạo quan hệ giữa hai node.
        """
        with self.driver.session() as session:
            query = (
                f"MATCH (a:{start_label} {{{start_key}: $start}}), (b:{end_label} {{{end_key}: $end}}) "
                f"MERGE (a)-[r:{rel_type}]->(b) "
                f"SET r += $props "
                f"RETURN r"
            )
            session.run(query, start=start_val, end=end_val, props=props or {})

    def list_relationships(self, start_label: str = None, end_label: str = None):
        """
        Liệt kê các quan hệ (option filter start_label, end_label).
        """
        with self.driver.session() as session:
            if start_label and end_label:
                query = f"MATCH (a:{start_label})-[r]->(b:{end_label}) RETURN a,r,b"
            else:
                query = "MATCH (a)-[r]->(b) RETURN a,r,b"
            result = session.run(query)
            return [
                {"start": dict(r["a"]), "relationship": dict(r["r"]), "end": dict(r["b"])}
                for r in result
            ]
