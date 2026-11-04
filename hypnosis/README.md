# Self-hypnosis sessions (personal use)

Four guided sessions for personal use. They are not for the YouTube channels.

| File | Length | Use it |
|---|---|---|
| `01-quit-smoking` | ~15 min | Once a day, starting a week before your quit day and continuing for 4 weeks after |
| `02-craving-rescue` | ~5 min | In the moment, whenever a craving hits (eyes open is fine) |
| `03-courage` | ~13 min | Before something you've been avoiding, or 3 to 5 times a week |
| `04-self-worth` | ~14 min | 3 to 5 times a week, ideally in the evening |

Use headphones, sit or lie somewhere safe, and **never listen while driving**. The `.m4a` files are audio only, for your phone.
All sessions share the same anchor: press your thumb and first finger together and breathe out slowly. The more you use it, the better it works.

## What the science actually says

**Hypnosis alone is not a proven quit method.** The Cochrane review (Barnes et al., 2019; 14 trials, 1,926 people) found
no clear evidence that hypnotherapy beats other approaches. Against equal-time counselling, the result was RR 1.21
(0.91 to 1.61), low certainty. That means "maybe a bit better, maybe the same". The largest single trial (Carmody et al., 2008, UCSF, n=286)
found 1-year quit rates of 22% with hypnosis vs 15% with counselling. That gap was not statistically significant overall, but hypnosis did
clearly better in people with a history of depression (27% vs 16%).
Across 49 meta-analyses, hypnosis works best when it is mixed with CBT-style techniques and when people also practise
self-hypnosis at home (Rosendahl et al., 2024). Live sessions sometimes beat recordings, but not always.

**What clearly works for quitting** (Cochrane, Livingstone-Banks et al., 2023):
- Varenicline more than doubles quit rates (RR 2.32, high certainty, 41 trials).
- Combination nicotine replacement (patch plus gum or lozenge) worked about as well as varenicline (RR 1.02, low certainty).
  Nicotine gum, lozenges and patches are sold over the counter in India.
- Quitline support adds to medication. **India National Tobacco Quit Line: 1800-112-356** (free). mCessation: give a missed call to 011-22901701.

**So the plan is: medication + quitline + these sessions.** The sessions are the extra layer, not a replacement.
See a doctor before starting varenicline, and also if you have heart disease, are pregnant, or take psychiatric medication.

### Techniques used, and the evidence for each

| Technique | Where | Evidence |
|---|---|---|
| Relaxation induction and slow breathing (exhale longer than inhale, about 6 breaths a minute) | all | Hypnosis for anxiety: d ≈ 0.8 across 15 trials (Valentine et al., 2019). Slow breathing lowers arousal. |
| Values self-affirmation | 1, 4 | 144 tests: improves health behaviour d = 0.32 (Epton et al., 2015) |
| Your own reasons (not lectures) | 1, 2 | Core of motivational interviewing |
| If-then plans ("If X, then I do Y") | 1, 3 | Medium-to-large effect on reaching goals, d = 0.65 across 94 tests (Gollwitzer and Sheeran, 2006) |
| Urge surfing (watch a craving rise and fall) | 1, 2 | Mindfulness-based relapse prevention (Bowen and Marlatt, 2009; Bowen et al., 2014) |
| Recalling past mastery, step-by-step rehearsal | 3 | Mastery experience is the strongest source of self-efficacy (Bandura). Imagined exposure reduces avoidance. |
| Compassionate self-talk | 4 | Self-compassion interventions: moderate effects on self-criticism and mood (Ferrari et al., 2019) |
| Best Possible Self imagery | 4 | Small-to-moderate boost to optimism and well-being (Carrillo et al., 2019) |
| Permissive "modern" wording, no disgust or fear suggestions | all | Modern hypnosis outperformed classical forms (Flammer and Alladin, 2007) |

**Deliberately left out:** big "I am amazing" affirmations. For people with low self-esteem, these made them feel *worse*
(Wood, Perunovic and Lee, 2009). Session 4 uses real evidence from your own life and a kind inner voice instead.
Binaural beats are also left out because the evidence for them is weak and mixed.

**Honest expectations:** some people respond to hypnosis much more strongly than others (hypnotisability correlates with
outcome, r ≈ 0.24). Daily practice for several weeks matters more than any single session.

## Build

```
pip install kokoro-onnx soundfile numpy pillow    # plus ffmpeg
# models: kokoro-v1.0.onnx + voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx releases (model-files-v1.0)
KOKORO_DIR=/path/to/models python hypnosis/build.py               # all sessions
KOKORO_DIR=/path/to/models python hypnosis/build.py --voice-test  # short clips of candidate voices
HYPNO_VOICE="bf_emma:1" HYPNO_SPEED=0.8 python hypnosis/build.py 01-quit-smoking
```

Scripts are plain text in `scripts/`. Each line is one spoken sentence, a blank line is a short rest, and `[pause N]` adds N seconds of quiet.
To make a session personal, edit the reasons and trigger moments in `01-quit-smoking.txt` so they use your own words.
Voice: offline Kokoro, a 60/40 blend of `af_heart` and `af_nicole` at 0.82 speed, with soft EQ and a small warm room.
Visuals: a glowing orb that breathes on a 10-second cycle (4 seconds in, 6 seconds out), with ripples on each exhale and slow aurora colours.
Fonts: Bodoni Moda (SIL OFL).

## Sources
- Barnes J et al. Hypnotherapy for smoking cessation. Cochrane 2019, CD001008. https://www.cochrane.org/evidence/CD001008
- Carmody TP et al. Hypnosis for smoking cessation: a randomized trial. Nicotine Tob Res 2008. https://pubmed.ncbi.nlm.nih.gov/18569754/
- Livingstone-Banks J et al. Nicotine receptor partial agonists for smoking cessation. Cochrane 2023, CD006103. https://pmc.ncbi.nlm.nih.gov/articles/PMC10169257/
- Rosendahl J et al. Efficacy of hypnosis: overview of 49 meta-analyses. Front Psychol 2024. https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1330238/pdf
- Epton T et al. The impact of self-affirmation on health-behavior change. Health Psychol 2015. https://pubmed.ncbi.nlm.nih.gov/25133846/
- Valentine KE et al. The efficacy of hypnosis as a treatment for anxiety. IJCEH 2019. https://pubmed.ncbi.nlm.nih.gov/31251710/
- Gollwitzer PM, Sheeran P. Implementation intentions and goal achievement. Adv Exp Soc Psychol 2006.
- Wood JV, Perunovic WQE, Lee JW. Positive self-statements: power for some, peril for others. Psychol Sci 2009.
- Ferrari M et al. Self-compassion interventions and psychosocial outcomes. Mindfulness 2019.
- Carrillo A et al. Effects of the Best Possible Self intervention. PLoS One 2019.
