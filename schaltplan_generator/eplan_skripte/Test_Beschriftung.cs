// Test: Laufen EPLAN-Skripte mit der vorhandenen Lizenz (P8 2025 Standard, ohne API)?
// UNGETESTET – Aufbau nach EPLAN-API-Doku "Scripts" und Aktion "label" (Konzept Q1, Q21).
//
// Vorbereitung:
//   1. In EPLAN ein Beschriftungs-Schema anlegen (Dienstprogramme > Auswertungen >
//      Beschriftung), Name "slpgen_Lernexport", Format Excel (*.xlsx), Inhalt:
//      BMK, Artikelnummer, Funktionstext, SPS-Adresse, Seite.
//   2. Ein Projekt im Seitennavigator markieren.
//   3. Datei > Extras > Schnittstellen > Skripte > "Ausführen" -> diese Datei wählen.
// Ergebnis:
//   Meldung "OK" und Datei vorhanden  -> Batch-Export ohne API möglich (Phase 1).
//   Lizenz-/Fehlermeldung              -> Export je Projekt über die GUI.
using Eplan.EplApi.ApplicationFramework;
using Eplan.EplApi.Scripting;

public class TestBeschriftung
{
    [Start]
    public void Ausfuehren()
    {
        ActionCallingContext ctx = new ActionCallingContext();
        ctx.AddParameter("CONFIGSCHEME", "slpgen_Lernexport");
        ctx.AddParameter("DESTINATIONFILE", @"C:\slpgen\export\test_beschriftung.xlsx");
        bool ok = new CommandLineInterpreter().Execute("label", ctx);
        System.Windows.Forms.MessageBox.Show(ok ? "OK – Beschriftung exportiert" : "Aktion 'label' fehlgeschlagen");
    }
}
