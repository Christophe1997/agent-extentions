# Testing Patterns (Chapter 27)

More detailed techniques for writing tests.

---

## Child Test

**Question**: How do you get a test case running that turns out to be too big?

**Answer**: Write a smaller test case that represents the broken part. Get the smaller test case running. Reintroduce the larger test case.

The Red/Green/Refactor rhythm requires keeping the red bar short. When a test is too big and has been red for more than ~10 minutes, something went wrong in planning. Write a smaller test that isolates just the broken part. Get that green first. Then reintroduce the original larger test.

When writing a test that turns out too big, first ask: "Why was it too big? What could I have done differently?" Then apply Child Test to restore momentum.

---

## Mock Object

**Question**: How do you test an object that relies on an expensive or unpredictable resource?

**Answer**: Create a fake version of the resource that answers constants.

When an object depends on a database, network, or clock, tests become slow, flaky, and environment-dependent. Replace the dependency with a mock (fake) that:
- Returns predictable, controlled values
- Can verify expected calls were made
- Runs in memory at test speed

Example — testing without a real database:
```java
// Real: Database db = new RealDatabase();
Database db = new MockDatabase();
db.expectQuery("SELECT ...", resultSet);
MyService service = new MyService(db);
service.doSomething();
db.verify();
```

Beyond speed: Mock Object forces design improvement. An object that's hard to mock has too many dependencies. Mocking exposes this and motivates decoupling.

---

## Self Shunt

**Question**: How do you test that one object communicates correctly with another?

**Answer**: Have the test case class implement the required interface and act as the collaborator itself.

Instead of creating a separate mock class:

```python
class TestResultTest(TestCase):
    # TestResultTest IS the listener
    def testNotification(self):
        result = TestResult()
        result.addListener(self)  # self IS the mock
        WasRun("testMethod").run(result)
        assert self.receivedNotification

    def startTest(self, test):  # implements listener protocol
        self.receivedNotification = True
```

Self Shunt works well for simple collaborators. For complex protocols, a separate mock object is clearer. The name comes from an electrical engineering term for a circuit that routes current through itself.

---

## Log String

**Question**: How do you test that a sequence of messages is called correctly?

**Answer**: Keep a log in a string; append each message as it is sent; assert on the string.

```python
class MockLog:
    def __init__(self):
        self.log = ""
    
    def setUp(self):
        self.log += "setUp "
    
    def testMethod(self):
        self.log += "testMethod "
    
    def tearDown(self):
        self.log += "tearDown "

test = MockLog("testMethod")
test.run()
assert "setUp testMethod tearDown " == test.log
```

Log String is useful for verifying ordering and sequencing of method calls. The string format makes failures immediately readable: "Expected 'setUp testMethod tearDown' but got 'testMethod setUp'."

---

## Crash Test Dummy

**Question**: How do you test error code that is unlikely to be triggered?

**Answer**: Create a special-purpose object that throws the exception instead of doing real work.

```java
void testFileSystemError() {
    File brokenFile = new File("foo/bar") {
        public boolean createNewFile() throws IOException {
            throw new IOException();
        }
    };
    try {
        saveAs(brokenFile);
        fail();
    } catch (SaveException expected) {
        // correct
    }
}
```

Crash Test Dummy is simpler than Mock Object — it only needs to trigger one specific failure path. Like a crash test dummy in automotive safety testing: it doesn't need to work like a person, just respond to the one collision scenario being tested.

---

## Broken Test

**Question**: How do you leave a programming session when you're programming alone?

**Answer**: Leave the last test broken.

End the solo session by writing a test case that fails. When you return, you have:
- An obvious place to start (make this test pass)
- A concrete reminder of where your thinking was
- A quick first win to restore momentum

The broken test doesn't make the program less finished — it makes the incompleteness explicit. The psychological benefit of a quick early win outweighs the minor discomfort of a red bar overnight.

---

## Clean Check-in

**Question**: How do you leave a programming session when you're programming in a team?

**Answer**: Leave all tests running.

When checking in on a team, all tests must pass. Teammates depend on a green baseline. Starting from broken tests is disorienting and wastes team time.

If you find broken tests in the integration suite when checking in:
- **Simplest rule**: throw away your work and start over (the broken test means you didn't know enough)
- **Alternative**: fix the defect and try again — but give up after a few minutes and start over

Commenting out tests to make the suite pass is strictly forbidden.
