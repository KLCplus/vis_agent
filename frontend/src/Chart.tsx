import {useEffect,useRef} from 'react';
import * as echarts from 'echarts';
export default function Chart({option,onClick,height=300}:{option:echarts.EChartsOption;onClick?:(p: any)=>void;height?:number}){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(!ref.current)return;const chart=echarts.init(ref.current,undefined,{renderer:'canvas'});chart.setOption(option);if(onClick)chart.on('click',onClick);const observer=new ResizeObserver(()=>chart.resize());observer.observe(ref.current);return()=>{observer.disconnect();chart.dispose()};},[option,onClick]);
 return <div ref={ref} style={{height,width:'100%'}} role="img" aria-label="交互分析图表"/>;
}
