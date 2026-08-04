using BepInEx;
using BepInEx.Logging;
using HarmonyLib;
using LitJson;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using Ostranauts.Core.Tutorials;
using Ostranauts.Objectives;
using UnityEngine;

namespace OstranautsRuTranslation
{
    [BepInPlugin("ru.nss.ostranautsrutranslation", "OstranautsRuTranslationNss", "3.0.0")]
    public class RuTranslation : BaseUnityPlugin
    {
        internal static ManualLogSource Log;
        private static readonly string InternalLogPath = Path.Combine(
            Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".",
            "BepInEx_RU_log.txt");

        private static void AppendInternalLog(string text)
        {
            try { File.AppendAllText(InternalLogPath, text); } catch { }
        }

        // Russian verb conjugations: key=infinitive, value=[1sg, 2sg, 3sg, 1pl, 2pl, 3pl]
        // Also keyed by 3sg form for backward compat with verbs.json that lists 3sg singulars.
        internal static Dictionary<string, string[]> VerbConjugations = new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase);
        internal static Dictionary<string, string[]> PastTenseStubs = new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase);
        internal static Dictionary<string, TutorialTranslation> TutorialTranslations = new Dictionary<string, TutorialTranslation>(StringComparer.OrdinalIgnoreCase);

        internal sealed class TutorialTranslation
        {
            public string Name;
            public string Desc;
            public string Complete;
        }

        // Strip a typical Russian 3sg ending to find the infinitive stem.
        // начнет -> начать, открывает -> открывать, говорит -> говорить, видит -> видеть,
        // пишет -> писать, берёт -> брать, жнёт -> жать
        internal static string TryGetInfinitive(string s)
        {
            if (string.IsNullOrEmpty(s)) return null;
            if (s.EndsWith("ется") || s.EndsWith("ится")) // возится -> возиться
            {
                return s.Substring(0, s.Length - 4) + "иться";
            }
            if (s.EndsWith("ает") || s.EndsWith("яет") || s.EndsWith("аёет")) // читает -> читать
            {
                return s.Substring(0, s.Length - 3) + "ать";
            }
            if (s.EndsWith("ует") || s.EndsWith("юет")) // рисует -> рисовать
            {
                return s.Substring(0, s.Length - 3) + "овать";
            }
            if (s.EndsWith("ёт") || s.EndsWith("ет")) // несёт -> нести, ведёт -> вести
            {
                return s.Substring(0, s.Length - 2) + "ти";
            }
            if (s.EndsWith("ит")) // говорит -> говорить
            {
                return s.Substring(0, s.Length - 2) + "ить";
            }
            return null;
        }

        private static void LoadConjugations()
        {
            string path = Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".", "verb_conjugations.json");
            try
            {
                if (!File.Exists(path))
                {
                    Log?.LogError($"[RU] verb_conjugations.json not found at {path}");
                    return;
                }
                string json = File.ReadAllText(path, Encoding.UTF8);
                var arr = JsonMapper.ToObject(json);
                int count = 0;
                foreach (JsonData item in (JsonData)arr["verbs"])
                {
                    string inf = (string)item["infinitive"];
                    var formsToken = (JsonData)item["forms"];
                    string[] forms = new string[6];
                    int i = 0;
                    foreach (JsonData f in (JsonData)formsToken)
                    {
                        if (i >= 6) break;
                        forms[i++] = (string)f;
                    }
                    while (i < 6) forms[i++] = inf;

                    VerbConjugations[inf] = forms;
                    // Also key by 3sg form
                    string sg3 = forms[2];
                    if (!string.IsNullOrEmpty(sg3) && !VerbConjugations.ContainsKey(sg3))
                        VerbConjugations[sg3] = forms;
                    count++;
                }
                Log?.LogInfo($"[RU] Loaded {count} verb conjugations from {path}");
            }
            catch (Exception ex)
            {
                Log?.LogError($"[RU] Failed to load verb_conjugations.json: {ex}");
            }

            // Hard-coded past-tense stubs (not very common, kept minimal)
            string[] pst(int n) { return new string[6] { n == 0 ? "был" : n == 1 ? "был" : n == 2 ? "был" : n == 3 ? "были" : n == 4 ? "были" : "были", "был", "был", "были", "были", "были" }; }
            // The real past-tense data lives in a separate JSON if needed; default to a generic stub
        }

        private static void LoadTutorialTranslations()
        {
            string path = Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? ".", "tutorial_translations.json");
            try
            {
                if (!File.Exists(path))
                {
                    Log?.LogWarning($"[RU] tutorial_translations.json not found at {path}");
                    return;
                }
                var root = JsonMapper.ToObject(File.ReadAllText(path, Encoding.UTF8));
                int count = 0;
                foreach (JsonData item in (JsonData)root["tutorials"])
                {
                    string type = (string)item["type"];
                    TutorialTranslations[type] = new TutorialTranslation
                    {
                        Name = item.Keys.Contains("name") ? (string)item["name"] : null,
                        Desc = item.Keys.Contains("desc") ? (string)item["desc"] : null,
                        Complete = item.Keys.Contains("complete") ? (string)item["complete"] : null
                    };
                    count++;
                }
                Log?.LogInfo($"[RU] Loaded {count} TutorialBeat translations from {path}");
            }
            catch (Exception ex)
            {
                Log?.LogError($"[RU] Failed to load tutorial_translations.json: {ex}");
            }
        }

        internal static string FormatTutorialText(string text)
        {
            if (string.IsNullOrEmpty(text)) return text;
            string[] glyphKeys = {
                "Pause", "Show Hotkeys & Interactables", "Click", "Player Inventory",
                "RightClick", "Quick Move Item", "Toggle PDA Power Vizor", "Turn CW",
                "Turn CCW", "Attitude", "Thrust Down", "Thrust Up", "Thrust Right",
                "Thrust Left", "Toggle station keeping"
            };
            foreach (string key in glyphKeys)
            {
                string marker = "{glyph:" + key + "}";
                if (text.Contains(marker))
                {
                    string glyph = GetInputGlyph(key);
                    if (!string.IsNullOrEmpty(glyph)) text = text.Replace(marker, glyph);
                }
            }
            return text;
        }

        private static string GetInputGlyph(string key)
        {
            try
            {
                Type type = AccessTools.TypeByName("InputManager") ?? AccessTools.TypeByName("Ostranauts.InputControl.InputManager");
                MethodInfo method = type?.GetMethod(
                    "GetGlyphString",
                    BindingFlags.Static | BindingFlags.Public,
                    null,
                    new Type[] { typeof(string), typeof(string) },
                    null);
                return method?.Invoke(null, new object[] { key, null }) as string;
            }
            catch { return null; }
        }

        internal static bool TryGetTutorialTranslation(TutorialBeat beat, out TutorialTranslation translation)
        {
            translation = null;
            return beat != null && TutorialTranslations.TryGetValue(beat.GetType().Name, out translation);
        }

        internal static void ApplyTutorialTranslation(TutorialBeat beat, Objective objective)
        {
            if (!TryGetTutorialTranslation(beat, out var tr) || objective == null) return;
            if (tr.Name != null) objective.strDisplayName = FormatTutorialText(tr.Name);
            if (tr.Desc != null) objective.strDisplayDesc = FormatTutorialText(tr.Desc);
            if (tr.Complete != null) objective.strDisplayDescComplete = FormatTutorialText(tr.Complete);
        }

        private void Awake()
        {
            try
            {
                Log = Logger;
                AppendInternalLog($"[{DateTime.Now}] Awake start\n");
                Log.LogInfo("[RU] Plugin starting...");

                LoadConjugations();
                LoadTutorialTranslations();
                ReplaceGrammarDictionaries();
                Log.LogInfo("[RU] Grammar replaced");

                try
                {
                    var harmony = new Harmony("ru.skobochki.rutranslation.v2");
                    harmony.PatchAll();
                    Log.LogInfo("[RU] Harmony patches applied");
                }
                catch (Exception ex)
                {
                    Log.LogError($"[RU] Harmony patches failed: {ex}");
                }

                AppendInternalLog($"[{DateTime.Now}] Plugin loaded: {VerbConjugations.Count} verb forms\n");
                Log.LogInfo("[RU] Ru Translation loaded");
            }
            catch (Exception ex)
            {
                AppendInternalLog($"[{DateTime.Now}] Awake ERROR: {ex}\n");
                Log?.LogError($"[RU] Awake failed: {ex}");
            }
        }

        private static void RegisterVerbsInDictVerbs()
        {
            try
            {
                var dictVerbsField = typeof(GrammarUtils).GetField("dictVerbs",
                    BindingFlags.Static | BindingFlags.Public);
                if (dictVerbsField == null) return;
                var dictVerbs = dictVerbsField.GetValue(null) as IDictionary;
                if (dictVerbs == null) return;

                int added = 0;
                foreach (var kvp in VerbConjugations)
                {
                    string key = kvp.Key;
                    string[] forms = kvp.Value;
                    if (forms == null || forms.Length < 6) continue;
                    // Game's Verb picks verbForms[0] for 3rd person, verbForms[1] for others.
                    // The Harmony Verb patch overrides this with full conjugation.
                    string[] verbForms = new string[2] { forms[2], forms[1] };
                    if (!dictVerbs.Contains(key))
                    {
                        dictVerbs[key] = verbForms;
                        added++;
                    }
                }
                Log?.LogInfo($"[RU] Added {added} Russian verbs to dictVerbs");
            }
            catch (Exception ex)
            {
                Log?.LogError($"[RU] RegisterVerbsInDictVerbs failed: {ex}");
            }
        }

        private void ReplaceGrammarDictionaries()
        {
            var bf = BindingFlags.Static | BindingFlags.Public;
            var pos = typeof(GrammarUtils).GetField("partsOfSpeech", bf)?.GetValue(null)
                as Dictionary<GrammarUtils.GrammarLUTIndex, string[]>;
            var posc = typeof(GrammarUtils).GetField("partsOfSpeechSentenceCase", bf)?.GetValue(null)
                as Dictionary<GrammarUtils.GrammarLUTIndex, string[]>;

            if (pos == null || posc == null)
            {
                Log?.LogError("[RU] Could not locate partsOfSpeech dictionaries");
                return;
            }

            string[] subj = { "я", "ты", "он", "она", "они", "оно" };
            string[] poss = { "мой", "твой", "его", "её", "их", "его" };
            string[] obj = { "меня", "тебя", "его", "её", "их", "его" };
            string[] refl = { "себя", "себя", "себя", "себя", "себя", "себя" };
            string[] cIs = { "я", "ты", "он", "она", "они", "оно" };
            string[] cHas = { "я", "ты", "у него", "у неё", "у них", "у него" };
            string[] cWill = { "я", "ты", "он", "она", "они", "оно" };
            string[] SubjS = { "Я", "Ты", "Он", "Она", "Они", "Оно" };
            string[] PossS = { "Мой", "Твой", "Его", "Её", "Их", "Его" };
            string[] ObjS = { "Меня", "Тебя", "Его", "Её", "Их", "Его" };
            string[] RefS = { "Себя", "Себя", "Себя", "Себя", "Себя", "Себя" };
            string[] CIsS = { "Я", "Ты", "Он", "Она", "Они", "Оно" };
            string[] CWillS = { "Я", "Ты", "Он", "Она", "Они", "Оно" };

            pos.Clear();
            posc.Clear();
            pos[GrammarUtils.GrammarLUTIndex.Subjective] = subj;
            pos[GrammarUtils.GrammarLUTIndex.Possessive] = poss;
            pos[GrammarUtils.GrammarLUTIndex.Objective] = obj;
            pos[GrammarUtils.GrammarLUTIndex.Reflexive] = refl;
            pos[GrammarUtils.GrammarLUTIndex.ContractIs] = cIs;
            pos[GrammarUtils.GrammarLUTIndex.ContractHas] = cHas;
            pos[GrammarUtils.GrammarLUTIndex.ContractWill] = cWill;
            posc[GrammarUtils.GrammarLUTIndex.Subjective] = SubjS;
            posc[GrammarUtils.GrammarLUTIndex.Possessive] = PossS;
            posc[GrammarUtils.GrammarLUTIndex.Objective] = ObjS;
            posc[GrammarUtils.GrammarLUTIndex.Reflexive] = RefS;
            posc[GrammarUtils.GrammarLUTIndex.ContractIs] = CIsS;
            posc[GrammarUtils.GrammarLUTIndex.ContractWill] = CWillS;

            Log?.LogInfo($"[RU] Grammar replaced: {pos.Count}/{posc.Count} entries");

            RegisterVerbsInDictVerbs();
        }
    }

    // GrammarUtils.PrepareToken only marks a token as a verb when the game's
    // dictVerbs contains the key. On some game/BepInEx load orders our runtime
    // registration happens before the game's token tables are rebuilt, leaving
    // valid JSON keys such as [сидит] as raw text. This prefix is a final
    // per-token fallback and does not depend on dictVerbs registration timing.
    [HarmonyPatch(typeof(DataHandler), "PrepareToken")]
    public static class Patch_GrammarUtils_PrepareToken
    {
        static void Prefix(ref TokenData t, string[] args)
        {
            try
            {
                if (args == null || args.Length != 1 || string.IsNullOrEmpty(args[0])) return;
                string key = args[0];
                if (RuTranslation.VerbConjugations == null ||
                    !RuTranslation.VerbConjugations.ContainsKey(key)) return;

                t.output = GrammarUtils.Verb;
                // Verb Prefix resolves the canonical 6-form array by this key;
                // the second value is only a compatibility fallback.
                t.verbForms = new string[2] { key, key };
            }
            catch
            {
                // Leave the game's original token preparation intact.
            }
        }
    }

    [HarmonyPatch(typeof(GrammarUtils), "Verb")]
    public static class Patch_GrammarUtils_Verb
    {
        static bool Prefix(ref TokenData tokenData)
        {
            try
            {
                var entityMapField = typeof(GrammarUtils).GetField("entityMap",
                    BindingFlags.Static | BindingFlags.Public);
                var outputField = typeof(GrammarUtils).GetField("interactionOutput",
                    BindingFlags.Static | BindingFlags.Public);

                var entityMap = entityMapField?.GetValue(null) as IDictionary;
                var sb = outputField?.GetValue(null) as StringBuilder;
                if (entityMap == null || sb == null) return true;

                if (!entityMap.Contains(tokenData.alias)) return true;
                var valueObj = entityMap[tokenData.alias];
                if (valueObj == null) return true;

                var inflectionField = valueObj.GetType().GetField("InflectionIndex",
                    BindingFlags.Instance | BindingFlags.Public);
                if (inflectionField == null) return true;
                int inflectionIdx = (int)inflectionField.GetValue(valueObj);

                if (tokenData.verbForms == null || tokenData.verbForms.Length == 0) return true;

                // Try verbForms[0] first, then verbForms[1], then derive infinitive from 3sg.
                if (RuTranslation.VerbConjugations == null || RuTranslation.VerbConjugations.Count == 0) return true;

                string[] conjugations = null;
                if (tokenData.verbForms.Length > 0)
                {
                    RuTranslation.VerbConjugations.TryGetValue(tokenData.verbForms[0], out conjugations);
                }
                if (conjugations == null && tokenData.verbForms.Length > 1)
                {
                    RuTranslation.VerbConjugations.TryGetValue(tokenData.verbForms[1], out conjugations);
                }
                if (conjugations == null)
                {
                    // Try to derive infinitive from 3sg form
                    foreach (var vf in tokenData.verbForms)
                    {
                        string inf = RuTranslation.TryGetInfinitive(vf);
                        if (inf != null && RuTranslation.VerbConjugations.TryGetValue(inf, out conjugations))
                            break;
                        conjugations = null;
                    }
                }
                if (conjugations == null) return true;

                int formIdx;
                if (inflectionIdx == 0) formIdx = 0;                          // First (1sg я)
                else if (inflectionIdx == 1) formIdx = 1;                     // Second (2sg ты)
                else if (inflectionIdx == 2 || inflectionIdx == 3) formIdx = 2; // 3sg м/ж
                else if (inflectionIdx == 4) formIdx = 5;                     // ThirdNeuter (3pl они)
                else if (inflectionIdx == 5) formIdx = 2;                     // ThirdNeuterNonHuman
                else formIdx = 2;

                if (formIdx >= conjugations.Length) formIdx = 2;
                string ruForm = conjugations[formIdx];

                if (GrammarUtils.Capitalise())
                {
                    if (ruForm.Length > 0)
                        ruForm = char.ToUpper(ruForm[0]) + ruForm.Substring(1);
                }
                sb.Append(ruForm);
                return false; // skip original
            }
            catch
            {
                return true;
            }
        }
    }

    // The base game prepends the English article "the " / "The " to
    // ThirdNeuterNonHuman proper names (items, doors, machines, etc.).
    // Russian does not need this hard-coded article, so remove only the
    // article inserted by AttemptProperName while preserving the item name.
    [HarmonyPatch(typeof(GrammarUtils), "AttemptProperName")]
    public static class Patch_GrammarUtils_AttemptProperName
    {
        static void Postfix(TokenData tokenData)
        {
            try
            {
                if (string.IsNullOrEmpty(tokenData.alias) ||
                    !GrammarUtils.entityMap.TryGetValue(tokenData.alias, out var entity) ||
                    entity == null ||
                    entity.InflectionIndex != GrammarUtils.PronounInflection.ThirdNeuterNonHuman)
                {
                    return;
                }

                var sb = GrammarUtils.interactionOutput;
                int caret = GrammarUtils.caret;
                // AttemptProperName sets caret to the final character of the
                // inserted four-character article, immediately before the name.
                if (sb == null || caret < 3 || caret >= sb.Length) return;
                string article = sb.ToString(caret - 3, 4);
                if (article == "the " || article == "The ")
                {
                    sb.Remove(caret - 3, 4);
                    GrammarUtils.caret = caret - 4;
                }
            }
            catch
            {
                // Never break the game's original proper-name rendering.
            }
        }
    }

    [HarmonyPatch(typeof(Objective), "MakeTutorialObjective")]
    public static class Patch_Objective_MakeTutorialObjective
    {
        static void Postfix(TutorialBeat tutorialBeat, Objective __result)
        {
            try { RuTranslation.ApplyTutorialTranslation(tutorialBeat, __result); }
            catch { }
        }
    }

    [HarmonyPatch(typeof(ObjectiveTracker), "AddObjective")]
    public static class Patch_ObjectiveTracker_AddObjective
    {
        static void Prefix(Objective objective)
        {
            try
            {
                if (objective != null && objective.TutorialBeat != null)
                    RuTranslation.ApplyTutorialTranslation(objective.TutorialBeat, objective);
            }
            catch { }
        }
    }

    // RestoreNavStation checks iA.strTitle == "Restore" in the vanilla code.
    // The translated interaction title is Russian, so use the stable internal
    // strDuty field as a fallback and keep the tutorial completion trigger.
    [HarmonyPatch(typeof(RestoreNavStation), "OnQuickActionButton")]
    public static class Patch_RestoreNavStation_QuickActionButton
    {
        static void Postfix(RestoreNavStation __instance, GUIQuickActionButton qab)
        {
            try
            {
                if (__instance == null || __instance.Finished || qab == null || qab.IA == null) return;
                var ia = qab.IA;
                if (ia.objThem != null && CrewSimTut.playerShipNavStationRef != null &&
                    ia.objThem.strID == CrewSimTut.playerShipNavStationRef.strID &&
                    ia.strDuty == "Restore")
                {
                    __instance.Finished = true;
                }
            }
            catch { }
        }
    }

    [HarmonyPatch(typeof(ObjectivePanel), "RefreshText")]
    public static class Patch_ObjectivePanel_RefreshText
    {
        static void Postfix(ObjectivePanel __instance)
        {
            try
            {
                var objectiveField = AccessTools.Field(typeof(ObjectivePanel), "_objective");
                var objective = objectiveField?.GetValue(__instance) as Objective;
                if (objective == null || objective.TutorialBeat == null ||
                    !RuTranslation.TryGetTutorialTranslation(objective.TutorialBeat, out var tr)) return;

                var titleField = AccessTools.Field(typeof(ObjectivePanel), "_txtTitle");
                var descField = AccessTools.Field(typeof(ObjectivePanel), "_txtDescription");
                if (titleField?.GetValue(__instance) is object title && tr.Name != null)
                    title.GetType().GetProperty("text")?.SetValue(title, RuTranslation.FormatTutorialText(tr.Name), null);
                if (descField?.GetValue(__instance) is object desc && tr.Desc != null)
                    desc.GetType().GetProperty("text")?.SetValue(desc, RuTranslation.FormatTutorialText(tr.Desc), null);
            }
            catch { }
        }
    }

    // The vanilla DataHandler.LoadPNG checks dictImages before checking the
    // files in aModPaths. If the core manual page was cached first, a later
    // mod replacement can never be seen. For manual pages, explicitly choose
    // the first existing file from a mod and fall back to StreamingAssets.
    [HarmonyPatch(typeof(DataHandler), "LoadPNG", new Type[] { typeof(string), typeof(bool), typeof(bool) })]
    public static class Patch_DataHandler_LoadPNG_ManualModPriority
    {
        private static readonly Dictionary<string, string> ManualImageSources =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        static bool Prefix(string strFileName, bool bNorm, bool alwaysLoadFreshInstance, ref Texture2D __result)
        {
            try
            {
                string key = (strFileName ?? string.Empty).Replace('\\', '/');
                if (!key.StartsWith("manuals/", StringComparison.OrdinalIgnoreCase))
                    return true;

                string selectedPath = FindFirstManualFile(key);
                if (selectedPath == null)
                    return true;

                if (!alwaysLoadFreshInstance &&
                    DataHandler.dictImages != null &&
                    DataHandler.dictImages.TryGetValue(key, out var cached) &&
                    cached != null &&
                    ManualImageSources.TryGetValue(key, out var cachedSource) &&
                    SamePath(cachedSource, selectedPath))
                {
                    __result = cached;
                    return false;
                }

                byte[] bytes = File.ReadAllBytes(selectedPath);
                Texture2D texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
                texture.filterMode = FilterMode.Point;
                texture.wrapMode = TextureWrapMode.Clamp;

                if (!TryLoadImage(texture, bytes))
                {
                    UnityEngine.Object.Destroy(texture);
                    LogWarning("Unable to decode manual PNG: " + selectedPath);
                    return true;
                }

                if (bNorm)
                    texture = ShaderSetup.NormalPNGtoDXTnm(texture);

                texture.name = key;
                if (DataHandler.dictImages != null)
                    DataHandler.dictImages[key] = texture;
                ManualImageSources[key] = selectedPath;
                __result = texture;

                bool isCore = IsInsideRoot(selectedPath, DataHandler.strAssetPath);
                RuTranslation.Log?.LogInfo("[RU] Manual PNG loaded from " +
                    (isCore ? "StreamingAssets" : "mod") + ": " + key +
                    " <- " + selectedPath + " (" + bytes.Length + " bytes)");
                return false;
            }
            catch (Exception ex)
            {
                RuTranslation.Log?.LogWarning("[RU] Manual PNG patch failed: " + ex.Message);
                return true;
            }
        }

        private static string FindFirstManualFile(string key)
        {
            string corePath = DataHandler.strAssetPath;
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            // The translation package can contain images without being added
            // to DataHandler.aModPaths (for example when its data folder is
            // not part of the game's data load). Search its real local-mod
            // directory explicitly before consulting the game's path list.
            foreach (string translationRoot in GetTranslationModRoots(corePath))
            {
                string path = BuildManualPath(translationRoot, key);
                if (path != null && seen.Add(path) && File.Exists(path))
                    return path;
            }

            // aModPaths is ordered with the highest-priority mod first. Skip
            // the core path here and add it explicitly as the final fallback.
            if (DataHandler.aModPaths != null)
            {
                foreach (string modPath in DataHandler.aModPaths)
                {
                    if (string.IsNullOrEmpty(modPath) || SamePath(modPath, corePath))
                        continue;
                    string path = BuildManualPath(modPath, key);
                    if (path != null && seen.Add(path) && File.Exists(path))
                        return path;
                }
            }

            string fallback = BuildManualPath(corePath, key);
            if (fallback != null && seen.Add(fallback) && File.Exists(fallback))
                return fallback;
            return null;
        }

        internal static List<string> GetTranslationModRoots(string corePath)
        {
            var roots = new List<string>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            if (!string.IsNullOrEmpty(DataHandler.strModFolder))
            {
                string root = Path.Combine(DataHandler.strModFolder, "ostranautsRuNss");
                if (seen.Add(root)) roots.Add(root);
            }

            try
            {
                string streamingRoot = corePath?.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                if (!string.IsNullOrEmpty(streamingRoot))
                {
                    DirectoryInfo streaming = new DirectoryInfo(streamingRoot);
                    DirectoryInfo dataRoot = streaming.Parent;
                    if (dataRoot != null)
                    {
                        string root = Path.Combine(dataRoot.FullName, "Mods", "ostranautsRuNss");
                        if (seen.Add(root)) roots.Add(root);
                    }
                }
            }
            catch { }
            return roots;
        }

        private static string BuildManualPath(string root, string key)
        {
            if (string.IsNullOrEmpty(root)) return null;
            return Path.Combine(root, "images", key.Replace('/', Path.DirectorySeparatorChar));
        }

        private static bool SamePath(string a, string b)
        {
            if (string.IsNullOrEmpty(a) || string.IsNullOrEmpty(b)) return false;
            try
            {
                return string.Equals(Path.GetFullPath(a).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar),
                    Path.GetFullPath(b).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar),
                    StringComparison.OrdinalIgnoreCase);
            }
            catch
            {
                return string.Equals(a, b, StringComparison.OrdinalIgnoreCase);
            }
        }

        private static bool IsInsideRoot(string filePath, string rootPath)
        {
            if (string.IsNullOrEmpty(filePath) || string.IsNullOrEmpty(rootPath)) return false;
            try
            {
                string file = Path.GetFullPath(filePath);
                string root = Path.GetFullPath(rootPath).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                return file.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) ||
                       file.StartsWith(root + Path.AltDirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
            }
            catch
            {
                return false;
            }
        }

        private static bool TryLoadImage(Texture2D texture, byte[] bytes)
        {
            Type imageConversion = AccessTools.TypeByName("UnityEngine.ImageConversion") ??
                Type.GetType("UnityEngine.ImageConversion, UnityEngine.ImageConversionModule");
            if (imageConversion == null) return false;

            foreach (MethodInfo method in imageConversion.GetMethods(BindingFlags.Public | BindingFlags.Static))
            {
                if (method.Name != "LoadImage") continue;
                ParameterInfo[] parameters = method.GetParameters();
                if (parameters.Length == 3 &&
                    parameters[0].ParameterType == typeof(Texture2D) &&
                    parameters[1].ParameterType == typeof(byte[]) &&
                    parameters[2].ParameterType == typeof(bool))
                {
                    object result = method.Invoke(null, new object[] { texture, bytes, false });
                    return !(result is bool) || (bool)result;
                }
                if (parameters.Length == 2 &&
                    parameters[0].ParameterType == typeof(Texture2D) &&
                    parameters[1].ParameterType == typeof(byte[]))
                {
                    object result = method.Invoke(null, new object[] { texture, bytes });
                    return !(result is bool) || (bool)result;
                }
            }
            return false;
        }

        private static void LogWarning(string message)
        {
            RuTranslation.Log?.LogWarning("[RU] " + message);
        }
    }

    // Unity 6 can leave a GUIManual RawImage with the texture assigned by an
    // earlier initialization pass. Re-apply the selected manual pages after
    // the game's SetPage method has finished, using the same mod-first loader.
    [HarmonyPatch(typeof(GUIManual), "SetPage", new Type[] { typeof(int) })]
    public static class Patch_GUIManual_SetPage_ManualModPriority
    {
        static void Postfix(GUIManual __instance)
        {
            try
            {
                var pages = AccessTools.Field(typeof(GUIManual), "aPages")?.GetValue(__instance) as IList;
                var indexObj = AccessTools.Field(typeof(GUIManual), "nIndex")?.GetValue(__instance);
                if (pages == null || !(indexObj is int)) return;

                int index = (int)indexObj;
                if (index >= 0 && index < pages.Count)
                    SetPageTexture(__instance, "bmpPageL", pages[index] as string);
                if (index + 1 >= 0 && index + 1 < pages.Count)
                    SetPageTexture(__instance, "bmpPageR", pages[index + 1] as string);
            }
            catch (Exception ex)
            {
                RuTranslation.Log?.LogWarning("[RU] GUIManual page patch failed: " + ex.Message);
            }
        }

        private static void SetPageTexture(GUIManual manual, string fieldName, string pageKey)
        {
            if (string.IsNullOrEmpty(pageKey)) return;
            object rawImage = AccessTools.Field(typeof(GUIManual), fieldName)?.GetValue(manual);
            if (rawImage == null) return;

            Texture2D texture = DataHandler.LoadPNG(pageKey, false);
            if (texture == null) return;

            PropertyInfo textureProperty = rawImage.GetType().GetProperty(
                "texture", BindingFlags.Instance | BindingFlags.Public);
            textureProperty?.SetValue(rawImage, texture, null);
        }
    }

    // DataHandler only loads interaction_overrides and plot_beat_overrides
    // from mods that were added to its data path list. The translation package
    // may still be present in the local Mods folder while its image files are
    // used separately. Inject both tables before vanilla AllPostLoadAsync
    // generates interactions and plot beats, so new missions receive the
    // translated definitions.
    [HarmonyPatch(typeof(DataHandler), "AllPostLoadAsync")]
    public static class Patch_DataHandler_AllPostLoadAsync_TranslationOverrides
    {
        private static bool loaded;

        static void Prefix()
        {
            if (loaded) return;
            loaded = true;

            try
            {
                int interactionAdded = 0;
                int plotBeatAdded = 0;
                foreach (string modRoot in Patch_DataHandler_LoadPNG_ManualModPriority.GetTranslationModRoots(DataHandler.strAssetPath))
                {
                    interactionAdded += LoadInteractionOverrides(modRoot);
                    plotBeatAdded += LoadPlotBeatOverrides(modRoot);
                }

                RuTranslation.Log?.LogInfo("[RU] Direct interaction overrides injected: " + interactionAdded);
                RuTranslation.Log?.LogInfo("[RU] Direct plot beat overrides injected: " + plotBeatAdded);
            }
            catch (Exception ex)
            {
                RuTranslation.Log?.LogError("[RU] Direct override patch failed: " + ex);
            }
        }

        private static int LoadInteractionOverrides(string modRoot)
        {
            if (DataHandler.dictIAOverrides == null) return 0;
            string directory = Path.Combine(modRoot, "data", "interaction_overrides");
            if (!Directory.Exists(directory)) return 0;

            int added = 0;
            foreach (string file in Directory.GetFiles(directory, "*.json", SearchOption.AllDirectories))
            {
                try
                {
                    JsonInteractionOverride[] overrides = JsonMapper.ToObject<JsonInteractionOverride[]>(
                        File.ReadAllText(file, Encoding.UTF8));
                    if (overrides == null) continue;
                    foreach (JsonInteractionOverride item in overrides)
                    {
                        if (item == null || string.IsNullOrEmpty(item.strName)) continue;
                        DataHandler.dictIAOverrides[item.strName] = item;
                        added++;
                    }
                    RuTranslation.Log?.LogInfo("[RU] Loaded interaction overrides directly: " + file);
                }
                catch (Exception ex)
                {
                    RuTranslation.Log?.LogError("[RU] Failed to load interaction overrides " + file + ": " + ex.Message);
                }
            }
            return added;
        }

        private static int LoadPlotBeatOverrides(string modRoot)
        {
            if (DataHandler.dictPlotBeatOverrides == null) return 0;
            string directory = Path.Combine(modRoot, "data", "plot_beat_overrides");
            if (!Directory.Exists(directory)) return 0;

            int added = 0;
            foreach (string file in Directory.GetFiles(directory, "*.json", SearchOption.AllDirectories))
            {
                try
                {
                    JsonPlotBeatOverride[] overrides = JsonMapper.ToObject<JsonPlotBeatOverride[]>(
                        File.ReadAllText(file, Encoding.UTF8));
                    if (overrides == null) continue;
                    foreach (JsonPlotBeatOverride item in overrides)
                    {
                        if (item == null || string.IsNullOrEmpty(item.strName)) continue;
                        DataHandler.dictPlotBeatOverrides[item.strName] = item;
                        added++;
                    }
                    RuTranslation.Log?.LogInfo("[RU] Loaded plot beat overrides directly: " + file);
                }
                catch (Exception ex)
                {
                    RuTranslation.Log?.LogError("[RU] Failed to load plot beat overrides " + file + ": " + ex.Message);
                }
            }
            return added;
        }
    }
}
