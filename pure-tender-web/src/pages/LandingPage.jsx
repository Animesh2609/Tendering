import { Link } from 'react-router-dom';
import { ArrowRight, FileText, Search, ShieldCheck } from 'lucide-react';
import PublicHeader from '../components/PublicHeader';
import HeroIllustration from '../components/HeroIllustration';
import TeamFooter from '../components/TeamFooter';

const journey = [
  { number: '01', title: 'Create a tender', description: 'The Lister enters the scope, expected value and dates. The tender goes through review before it becomes public.' },
  { number: '02', title: 'Receive bids', description: 'Bidders check the requirements and upload their proposal before the submission deadline.' },
  { number: '03', title: 'Review and decide', description: 'Evaluators assess eligible bids. The Auditor checks integrity records before the final decision.' },
];

const responsibilities = [
  { icon: FileText, title: 'For organizations', items: ['Keep tender information in one place', 'Follow the status of each request', 'Manage proposals through a defined process'] },
  { icon: Search, title: 'For bidders', items: ['Find published opportunities', 'Read requirements before applying', 'Keep track of your own submissions'] },
];

export default function LandingPage() {
  return (
    <>
      <PublicHeader />
      <main id="home">
        <section className="tb-landing-hero border-b border-[#e6e5f2] dark:border-slate-800">
          <div className="tb-container grid items-center gap-12 py-16 lg:grid-cols-[1fr_.92fr] lg:gap-16 lg:py-24">
            <div>
              <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#e3e0ff] bg-white/75 px-4 py-2 text-xs font-extrabold uppercase tracking-[.12em] text-[#5b4bda] shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-violet-300">
                <span className="h-2 w-2 rounded-full bg-[#5b4bda]"/> TenderBlock procurement marketplace
              </p>
              <h1 className="max-w-[660px] text-[clamp(2.7rem,5vw,4.7rem)] leading-[1.04] tracking-[-.055em] text-[#20243f] dark:text-slate-100">
                Find the right opportunity. <span className="text-[#5b4bda]">Make your next move.</span>
              </h1>
              <p className="mt-6 max-w-[520px] text-[16px] leading-8 text-[#65677d] dark:text-slate-300">
                Discover published tenders, submit proposals and follow every decision in one clear, trusted workspace.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-4">
                <Link to="/register" className="tb-btn-primary">Get started <ArrowRight size={16} /></Link>
                <a href="#process" className="text-sm font-bold text-[#5748cf] underline decoration-[#bcb6f2] underline-offset-4 hover:text-[#4334b8] dark:text-slate-200">See how it works</a>
              </div>
              <p className="mt-8 border-l-2 border-[#8a7ef0] pl-4 text-xs leading-6 text-[#686a7e] dark:text-slate-400">
                Public accounts are for Bidders and Listers. Admin, Evaluator and Auditor accounts use a separate staff sign-in.
              </p>
            </div>
            <HeroIllustration />
          </div>
        </section>

        <section id="about" className="bg-white py-16 dark:bg-slate-900 lg:py-20">
          <div className="tb-container grid gap-10 lg:grid-cols-[.55fr_1fr] lg:gap-20">
            <div>
              <p className="tb-eyebrow">01 / Overview</p>
              <h2 className="tb-section-title mt-3">Why we built this</h2>
            </div>
            <div className="max-w-[730px]">
              <p className="text-[17px] leading-8 text-[#394e5a] dark:text-slate-200">
                Tendering involves several people, deadlines and documents. Information can get scattered between emails, spreadsheets and separate approval records. Our project brings those steps together so the people involved know what needs attention.
              </p>
              <p className="mt-4 text-sm leading-7 text-slate-600 dark:text-slate-300">
                The system uses role-based access and is being connected to a Spring Boot backend. Hyperledger Fabric is intended to record evidence of key actions and document integrity. Those ledger functions depend on the deployed backend and network.
              </p>
            </div>
          </div>
        </section>

        <section id="features" className="border-y border-[#e2e5e3] bg-[#f7f8f6] py-16 dark:border-slate-800 dark:bg-slate-950 lg:py-20">
          <div className="tb-container">
            <p className="tb-eyebrow">02 / Who uses it</p>
            <h2 className="tb-section-title mt-3">Two sides of the same tender</h2>
            <div className="mt-8 grid gap-5 md:grid-cols-2">
              {responsibilities.map(({ icon: Icon, title, items }) => (
                <article key={title} className="tb-card p-7 sm:p-9">
                  <div className="mb-5 flex items-center gap-3">
                    <div className="grid h-11 w-11 place-items-center rounded-md bg-[#eef2f1] text-[#315d64] dark:bg-slate-700 dark:text-slate-200"><Icon size={22} /></div>
                    <h3 className="text-xl font-semibold tracking-tight text-[#243741] dark:text-slate-100">{title}</h3>
                  </div>
                  <ul className="space-y-3 text-sm leading-6 text-[#4c5d63] dark:text-slate-300">
                    {items.map(item => <li key={item} className="flex gap-3"><span className="mt-[11px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#b88950]" />{item}</li>)}
                  </ul>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="process" className="bg-white py-16 dark:bg-slate-900 lg:py-20">
          <div className="tb-container">
            <p className="tb-eyebrow">03 / Process</p>
            <h2 id="how-it-works" className="tb-section-title mt-3">How a tender moves through the system</h2>
            <div className="mt-9 grid gap-8 border-t border-slate-200 pt-8 dark:border-slate-700 md:grid-cols-3">
              {journey.map(step => (
                <article key={step.number} className="pr-5">
                  <span className="font-serif text-4xl text-[#bd905f] dark:text-[#dcb17b]">{step.number}</span>
                  <h3 className="mt-5 text-lg font-semibold text-[#203744] dark:text-slate-100">{step.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-slate-600 dark:text-slate-300">{step.description}</p>
                </article>
              ))}
            </div>
            <div className="mt-10 flex flex-wrap items-center gap-3 rounded-lg border border-[#e3e6e4] bg-[#f8f9f7] px-5 py-4 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <ShieldCheck size={18} className="shrink-0 text-[#52716b] dark:text-slate-300" />
              <span>Evaluation and auditing are separate steps. A strong proposal and an unchanged document are not the same thing.</span>
            </div>
          </div>
        </section>

        <section className="bg-[#203b4d] py-11 text-white">
          <div className="tb-container flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
            <div>
              <h2 className="font-serif text-2xl sm:text-3xl">Start with your organization.</h2>
              <p className="mt-2 text-sm text-slate-200">Register as a Bidder or a Lister to use the public portal.</p>
            </div>
            <Link to="/register" className="inline-flex items-center justify-center gap-2 self-start rounded-md bg-white px-5 py-3 text-sm font-semibold text-[#203b4d] hover:bg-[#f0ede6] sm:self-auto">
              Create account <ArrowRight size={16} />
            </Link>
          </div>
        </section>
      </main>
      <TeamFooter />
    </>
  );
}
