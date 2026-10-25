### The teacher this is for

I taught high-school Spanish. The task that consumed the most time, and the
one I did worst, was not grading. It was diagnosis.

Grading an essay is quick: read it, mark the errors, put a number on it.
Diagnosing is different. It means answering *what is this specific student
missing, and what should they do next?* — and doing it thirty times, for
thirty different students, every time you collect a set of compositions. A
proficiency-oriented teacher is supposed to work against the ACTFL
Proficiency Guidelines, which describe writing along four criteria (Functions
and tasks, Accuracy, Context and content, Text type) across eleven sublevels.
Done properly, for one composition, that is ten to fifteen minutes of work.

Thirty students, every two weeks, at twelve minutes each is six hours a
fortnight. Nobody has six hours a fortnight. So what actually happens is what
I did: mark the errors, write *good work, watch your preterite*, hand it back,
and move on. The student learns which words were wrong. They learn nothing
about what is holding them one rung below where they could be.

### Why the paper matters

Three details make this harder than it sounds, and all three are why a
general-purpose AI tool does not solve it.

**The work is on paper.** Language teachers collect handwriting, because
typing invites autocorrect, translation tools, and a keyboard that supplies
the accents the student is supposed to know. Every AI writing tool I am aware
of assumes typed input. Getting the work into a tool means someone retypes
thirty compositions.

**The errors are the data.** A missing accent, `tambien` for `también`, is
not noise to be cleaned up on the way in. Under ACTFL it is evidence about
Accuracy. Any transcription step that helpfully corrects it has destroyed the
measurement before the assessment begins.

**A score is not a diagnosis.** Knowing a composition is "Intermediate Low"
tells a student nothing actionable. Knowing that *Text Type* is what holds
them there — that they write correct sentences but never link them into a
paragraph — tells them exactly what to practise next.

### What this costs today

| | today | with this app |
|---|---|---|
| Time per composition | 10–15 min to do properly | about 30 s, plus teacher review |
| What the student receives | error marks and a grade | the criterion blocking the next sublevel, with practice aimed at it |
| What usually happens instead | a grade and a general comment | — |
| Cost per composition | teacher time | {{"${:.3f}".format(f['typical']['cost_usd'])}} |

The honest version of the time claim: the app does not replace the teacher's
judgement, and it is not meant to. It does the first pass — transcribe,
locate evidence against each criterion, name the blocking one, draft the
practice — and hands a teacher something to correct rather than a blank page
to start from. The measured review step is the transcript confirmation
screen, which takes under a minute.
