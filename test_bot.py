import os
import asyncio
import unittest
from localization import to_bold, get_text
import database

# Mock classes for MongoDB driver (motor) to support unit tests without a running database
class MockCursor:
    def __init__(self, data):
        self.data = data
        self.idx = 0
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.idx < len(self.data):
            val = self.data[self.idx]
            self.idx += 1
            return val
        raise StopAsyncIteration

class MockCollection:
    def __init__(self):
        self.docs = {} # _id -> doc
        
    async def find_one(self, query):
        _id = query.get("_id")
        if _id in self.docs:
            return dict(self.docs[_id])
        # simple scanning mock
        for doc in self.docs.values():
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                return dict(doc)
        return None
        
    async def update_one(self, filter_query, update_query, upsert=False):
        _id = filter_query.get("_id")
        doc = self.docs.get(_id)
        
        is_insert = False
        if not doc:
            if upsert:
                is_insert = True
                doc = {"_id": _id}
                self.docs[_id] = doc
            else:
                return
                
        # Handle $set
        set_fields = update_query.get("$set", {})
        for k, v in set_fields.items():
            doc[k] = v
            
        # Handle $setOnInsert
        if is_insert:
            setOnInsert_fields = update_query.get("$setOnInsert", {})
            for k, v in setOnInsert_fields.items():
                doc[k] = v
                
        # Handle $inc
        inc_fields = update_query.get("$inc", {})
        for k, v in inc_fields.items():
            doc[k] = doc.get(k, 0) + v
            
    async def count_documents(self, filter_query):
        count = 0
        for doc in self.docs.values():
            match = True
            for k, v in filter_query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                count += 1
        return count
        
    async def delete_one(self, filter_query):
        _id = filter_query.get("_id")
        if _id in self.docs:
            del self.docs[_id]
            
    def find(self, filter_query):
        matches = []
        for doc in self.docs.values():
            match = True
            for k, v in filter_query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                matches.append(dict(doc))
        return MockCursor(matches)
        
    def aggregate(self, pipeline):
        # Extremely simplified aggregate mock for statistics aggregation
        group_stage = pipeline[0].get("$group", {})
        group_id = group_stage.get("_id")
        
        results = []
        if group_id == "$lang":
            lang_counts = {}
            for doc in self.docs.values():
                lang = doc.get("lang")
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            for lang, count in lang_counts.items():
                results.append({"_id": lang, "count": count})
        elif group_id is None:
            sum_field = group_stage.get("total", {}).get("$sum", "")
            if sum_field.startswith("$"):
                field_name = sum_field[1:]
                total = sum(doc.get(field_name, 0) for doc in self.docs.values())
                results.append({"_id": None, "total": total})
                
        return MockCursor(results)

class MockDatabase:
    def __init__(self):
        self.users = MockCollection()
        self.chats = MockCollection()
        self.force_subs = MockCollection()
        self.settings = MockCollection()
        self.bulk_jobs = MockCollection()

# Setup database.db mock environment
mock_db = MockDatabase()
database.db = mock_db

async def mock_init_db():
    defaults = {
        "fsub_enabled": "0",
        "verification_enabled": "0",
        "bulk_enabled": "1",
        "approval_speed": "160"
    }
    for k, v in defaults.items():
        await database.db.settings.update_one(
            {"_id": k},
            {"$setOnInsert": {"value": v}},
            upsert=True
        )

# Patch init_db
database.init_db = mock_init_db


class TestJoinRequestBot(unittest.TestCase):
    
    def test_bold_translation(self):
        # Normal alphanumeric conversion
        self.assertEqual(to_bold("Hello 123"), "𝗛𝗲𝗹𝗹𝗼 𝟭𝟮𝟯")
        
        # Verify tag retention (should not bold HTML tags)
        self.assertEqual(to_bold("<b>Hello</b>"), "<b>𝗛𝗲𝗹𝗹𝗼</b>")
        self.assertEqual(to_bold("<a href='https://t.me/test'>link</a>"), "<a href='https://t.me/test'>𝗹𝗶𝗻𝗸</a>")
        
        # Verify link retention (should not bold invite link URLs or usernames)
        self.assertEqual(to_bold("https://t.me/Venom_Stone_Network"), "https://t.me/Venom_Stone_Network")
        self.assertEqual(to_bold("t.me/Venom_Stone_Network"), "t.me/Venom_Stone_Network")
        self.assertEqual(to_bold("@Venom_Stone_Network"), "@Venom_Stone_Network")
        
        # Mixed check
        self.assertEqual(
            to_bold("Join @Venom_Stone_Network for updates! Details at https://t.me/link"),
            "𝗝𝗼𝗶𝗻 @Venom_Stone_Network 𝗳𝗼𝗿 𝘂𝗽𝗱𝗮𝘁𝗲𝘀! 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 𝗮𝘁 https://t.me/link"
        )
        
    def test_localization_retrieval(self):
        # English fallback and formatting
        text = get_text("verify_msg", lang="en", chat_title="My Chat")
        self.assertIn("𝗠𝘆 𝗖𝗵𝗮𝘁", text)
        self.assertIn("𝗛𝗲𝗹𝗹𝗼", text)
        
        # Hindi language retrieval
        text_hi = get_text("verify_msg", lang="hi", chat_title="चैट")
        self.assertIn("साबित", text_hi)


class TestDatabase(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        # Clear mock collections before each test run
        mock_db.users.docs.clear()
        mock_db.chats.docs.clear()
        mock_db.force_subs.docs.clear()
        mock_db.settings.docs.clear()
        mock_db.bulk_jobs.docs.clear()
            
    async def test_db_operations(self):
        # Test initialization
        await database.init_db()
        
        # Test default settings loading
        fsub_enabled = await database.get_setting("fsub_enabled")
        self.assertEqual(fsub_enabled, "0")
        
        # Test user addition and query
        await database.add_user(123456, "test_user")
        user = await database.get_user(123456)
        self.assertIsNotNone(user)
        self.assertEqual(user["user_id"], 123456)
        self.assertEqual(user["username"], "test_user")
        self.assertEqual(user["is_verified"], 0)
        
        # Test verification toggle
        await database.set_user_verified(123456, True)
        user = await database.get_user(123456)
        self.assertEqual(user["is_verified"], 1)
        
        # Test settings updating
        await database.set_setting("fsub_enabled", "1")
        fsub_enabled = await database.get_setting("fsub_enabled")
        self.assertEqual(fsub_enabled, "1")
        
        # Test chat insertion and fetch
        await database.add_chat(987654321, "Test Chat", "channel", "testchannel", 123456)
        chat = await database.get_chat(987654321)
        self.assertIsNotNone(chat)
        self.assertEqual(chat["chat_title"], "Test Chat")
        
        # Test stats query
        stats = await database.get_db_stats()
        self.assertEqual(stats["total_users"], 1)
        self.assertEqual(stats["verified_users"], 1)
        self.assertEqual(stats["total_chats"], 1)

if __name__ == "__main__":
    unittest.main()
