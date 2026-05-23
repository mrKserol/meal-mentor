import type { DiaryPeriodDay, DiarySnapshot, DiaryWeekDay } from "../../types/diary";

export type ChartDay = DiaryWeekDay | DiaryPeriodDay;

export const ANALYSIS_GROUPS: {
  title: string;
  items: Array<{ key: string; label: string; unit: string }>;
}[] = [
  {
    title: "Витамины",
    items: [
      { key: "vitamin_a_iu", label: "Витамин A", unit: "МЕ" },
      { key: "vitamin_a_rae_mcg", label: "Витамин A RAE", unit: "мкг" },
      { key: "vitamin_c_mg", label: "Витамин C", unit: "мг" },
      { key: "vitamin_d_iu", label: "Витамин D", unit: "МЕ" },
      { key: "vitamin_e_mg", label: "Витамин E", unit: "мг" },
      { key: "tocopherol_alpha_mg", label: "Альфа-токоферол", unit: "мг" },
      { key: "vitamin_k_mcg", label: "Витамин K", unit: "мкг" },
      { key: "thiamin_mg", label: "Витамин B1 / тиамин", unit: "мг" },
      { key: "riboflavin_mg", label: "Витамин B2 / рибофлавин", unit: "мг" },
      { key: "niacin_mg", label: "Витамин B3 / ниацин", unit: "мг" },
      { key: "pantothenic_acid_mg", label: "Витамин B5 / пантотеновая кислота", unit: "мг" },
      { key: "vitamin_b6_mg", label: "Витамин B6", unit: "мг" },
      { key: "folate_mcg", label: "Витамин B9 / фолат", unit: "мкг" },
      { key: "folic_acid_mcg", label: "Фолиевая кислота", unit: "мкг" },
      { key: "vitamin_b12_mcg", label: "Витамин B12", unit: "мкг" },
      { key: "choline_mg", label: "Холин", unit: "мг" },
    ],
  },
  {
    title: "Каротиноиды",
    items: [
      { key: "carotene_alpha_mcg", label: "Альфа-каротин", unit: "мкг" },
      { key: "carotene_beta_mcg", label: "Бета-каротин", unit: "мкг" },
      { key: "cryptoxanthin_beta_mcg", label: "Бета-криптоксантин", unit: "мкг" },
      { key: "lutein_zeaxanthin_mcg", label: "Лютеин + зеаксантин", unit: "мкг" },
      { key: "lycopene_mcg", label: "Ликопин", unit: "мкг" },
    ],
  },
  {
    title: "Минералы",
    items: [
      { key: "calcium_mg", label: "Кальций", unit: "мг" },
      { key: "magnesium_mg", label: "Магний", unit: "мг" },
      { key: "potassium_mg", label: "Калий", unit: "мг" },
      { key: "phosphorus_mg", label: "Фосфор", unit: "мг" },
      { key: "iron_mg", label: "Железо", unit: "мг" },
      { key: "zinc_mg", label: "Цинк", unit: "мг" },
      { key: "selenium_mcg", label: "Селен", unit: "мкг" },
      { key: "copper_mg", label: "Медь", unit: "мг" },
      { key: "manganese_mg", label: "Марганец", unit: "мг" },
      { key: "sodium_mg", label: "Натрий", unit: "мг" },
    ],
  },
  {
    title: "Аминокислоты",
    items: [
      { key: "alanine_g", label: "Аланин", unit: "г" },
      { key: "arginine_g", label: "Аргинин", unit: "г" },
      { key: "aspartic_acid_g", label: "Аспарагиновая кислота", unit: "г" },
      { key: "cystine_g", label: "Цистин", unit: "г" },
      { key: "glutamic_acid_g", label: "Глутаминовая кислота", unit: "г" },
      { key: "glycine_g", label: "Глицин", unit: "г" },
      { key: "histidine_g", label: "Гистидин", unit: "г" },
      { key: "hydroxyproline_g", label: "Гидроксипролин", unit: "г" },
      { key: "isoleucine_g", label: "Изолейцин", unit: "г" },
      { key: "leucine_g", label: "Лейцин", unit: "г" },
      { key: "lysine_g", label: "Лизин", unit: "г" },
      { key: "methionine_g", label: "Метионин", unit: "г" },
      { key: "phenylalanine_g", label: "Фенилаланин", unit: "г" },
      { key: "proline_g", label: "Пролин", unit: "г" },
      { key: "serine_g", label: "Серин", unit: "г" },
      { key: "threonine_g", label: "Треонин", unit: "г" },
      { key: "tryptophan_g", label: "Триптофан", unit: "г" },
      { key: "tyrosine_g", label: "Тирозин", unit: "г" },
      { key: "valine_g", label: "Валин", unit: "г" },
    ],
  },
  {
    title: "Липиды и жирные кислоты",
    items: [
      { key: "fat_g", label: "Жиры всего", unit: "г" },
      { key: "saturated_fat_g", label: "Насыщенные жиры", unit: "г" },
      { key: "monounsaturated_fatty_acids_g", label: "Мононенасыщенные", unit: "г" },
      { key: "polyunsaturated_fatty_acids_g", label: "Полиненасыщенные", unit: "г" },
      { key: "cholesterol_mg", label: "Холестерин", unit: "мг" },
    ],
  },
  {
    title: "Сахара",
    items: [
      { key: "sugar_g", label: "Сахара всего", unit: "г" },
      { key: "fructose_g", label: "Фруктоза", unit: "г" },
      { key: "glucose_g", label: "Глюкоза", unit: "г" },
      { key: "lactose_g", label: "Лактоза", unit: "г" },
      { key: "galactose_g", label: "Галактоза", unit: "г" },
      { key: "maltose_g", label: "Мальтоза", unit: "г" },
      { key: "sucrose_g", label: "Сахароза", unit: "г" },
    ],
  },
  {
    title: "Дополнительно",
    items: [
      { key: "water_g", label: "Вода", unit: "г" },
      { key: "alcohol_g", label: "Алкоголь", unit: "г" },
      { key: "caffeine_mg", label: "Кофеин", unit: "мг" },
      { key: "theobromine_mg", label: "Теобромин", unit: "мг" },
    ],
  },
];

export function chartDayLabel(d: ChartDay): string {
  if ("weekday_short" in d && typeof d.weekday_short === "string" && d.weekday_short.length > 0) {
    return d.weekday_short;
  }
  const dayOfMonth = Number(d.date.slice(8, 10));
  return Number.isFinite(dayOfMonth) && dayOfMonth > 0 ? String(dayOfMonth) : (d as DiaryPeriodDay).label;
}

export function formatFixedRu(n: number, frac = 1): string {
  return new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: frac }).format(n);
}

type PeriodStats = DiarySnapshot["week"] | DiarySnapshot["month"] | null;

export function nutrientProfileValueMeals(activeStats: PeriodStats, key: string): number {
  if (!activeStats) return 0;
  return activeStats.detailed_avg_meals?.[key] ?? 0;
}

export function nutrientProfileValueAdditives(activeStats: PeriodStats, key: string): number {
  if (!activeStats) return 0;
  return activeStats.detailed_avg_additives?.[key] ?? 0;
}

/** @deprecated use nutrientProfileValueMeals / nutrientProfileValueAdditives */
export function nutrientProfileValue(activeStats: PeriodStats, key: string): number {
  if (!activeStats) return 0;
  if (key === "fat_g") return activeStats.avg_fat_g ?? 0;
  if (key === "sugar_g") return activeStats.avg_sugar_g ?? 0;
  if (key === "saturated_fat_g") return activeStats.avg_saturated_fat_g ?? 0;
  return activeStats.detailed_avg?.[key] ?? 0;
}

export function nutrientProfileRowVisible(mealsVal: number, addVal: number): boolean {
  return Math.abs(mealsVal) > 1e-6 || Math.abs(addVal) > 1e-6;
}

export function nutrientProfilePeriodTitle(period: "week" | "month"): string {
  return period === "week"
    ? "Средние суточные значения за неделю"
    : "Средние суточные значения за месяц";
}

export function nutrientProfileFracDigits(key: string): number {
  if (key === "calories") return 0;
  if (["protein_g", "fat_g", "carbs_g", "fiber_g", "sugar_g"].includes(key)) return 1;
  if (
    [
      "calcium_mg",
      "magnesium_mg",
      "potassium_mg",
      "phosphorus_mg",
      "iron_mg",
      "zinc_mg",
      "copper_mg",
      "manganese_mg",
      "sodium_mg",
      "cholesterol_mg",
    ].includes(key)
  ) {
    return 0;
  }
  if (["caffeine_mg", "theobromine_mg"].includes(key)) return 1;
  if (key.endsWith("_mcg") || key.endsWith("_iu")) return 0;
  if (key.endsWith("_g")) return 2;
  return 1;
}
